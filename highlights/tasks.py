from celery import shared_task
from django.utils import timezone
import os
import shutil

from .models import ProcessingJob, Project, VideoAsset, Segment
from services.video_pipeline.progress import update_job_progress


@shared_task(bind=True, max_retries=3)
def process_video_job(self, job_id: str) -> None:
    from core.audio_analyzer import AudioAnalyzer
    from core.video_segmenter import VideoSegmenter
    from core.vision_analyzer import VisionAnalyzer

    print(f"DEBUG Task: Lancement pour le job {job_id}")
    job = ProcessingJob.objects.select_related("project").get(id=job_id)
    video_asset = VideoAsset.objects.get(project=job.project)
    video_path = video_asset.file.path
    
    # Check if file exists
    if not os.path.exists(video_path):
        # Maybe it's a relative path in dev?
        # In a real environment, we'd handle storage backends.
        pass

    try:
        # Step 1: Detect Events (Audio + Video)
        update_job_progress(job, progress=10, step="event_detection", message="Détection des évènements (Audio)...")
        audio_analyzer = AudioAnalyzer(video_path)
        audio_analyzer.extract_audio()
        audio_peaks = audio_analyzer.get_excitement_peaks(threshold_factor=1.2, min_distance_sec=12)
        focus_windows = build_focus_windows(audio_peaks)
        if focus_windows:
            print(f"DEBUG Task: Focus windows for vision: {len(focus_windows)}")
        
        update_job_progress(job, progress=30, step="event_detection", message="Détection visuelle (YOLOv8)...")
        vision_analyzer = VisionAnalyzer(video_path)
        vision_peaks = vision_analyzer.analyze_events(sample_rate=1.0, focus_windows=focus_windows, focus_sample_rate=2.5)
        
        # Merge peaks
        all_peaks = merge_peaks(audio_peaks, vision_peaks)
        print(f"DEBUG Task: {len(all_peaks)} évènements détectés au total.")
        
        # Step 2: Segment & Render
        update_job_progress(job, progress=60, step="render", message="Création du montage final...")
        segmenter = VideoSegmenter(video_path)
        # On passe les pics avec leurs labels pour un montage plus intelligent
        output_path = segmenter.create_highlights(all_peaks, target_duration_mins=job.target_duration_minutes)
        
        # Step 3: Finalize
        if output_path and os.path.exists(output_path):
            output_abs = os.path.abspath(output_path)
            
            if job.output_destination:
                # Nettoyage et normalisation du chemin pour Windows
                target = job.output_destination.strip()
                if os.name == 'nt' and '/' in target:
                    target = target.replace('/', '\\')
                
                # Détermine si la destination est un dossier ou un fichier spécifique
                has_extension = bool(os.path.splitext(target)[1])
                is_dir = os.path.isdir(target) or not has_extension
                
                if is_dir:
                    dest_dir = target
                    # Supprime l'extension du titre pour éviter .mp4.mp4
                    clean_title = os.path.splitext(job.project.title)[0]
                    final_path = os.path.join(dest_dir, f"highlight_{clean_title}.mp4")
                else:
                    dest_dir = os.path.dirname(target)
                    final_path = target

                # Création robuste du dossier de destination
                if dest_dir and not os.path.exists(dest_dir):
                    print(f"DEBUG Task: Création du dossier de destination: {dest_dir}")
                    os.makedirs(dest_dir, exist_ok=True)
                
                final_abs = os.path.abspath(final_path)
                print(f"DEBUG Task: Déplacement final: {output_abs} -> {final_abs}")
                
                # Utilisation de copy + remove si move échoue entre différents disques
                try:
                    shutil.move(output_abs, final_abs)
                except OSError:
                    shutil.copy2(output_abs, final_abs)
                    os.remove(output_abs)
                
                output_path = final_abs

            # Save segments for preview
            for peak_time, score, label in all_peaks:
                Segment.objects.create(
                    job=job,
                    start_time=max(0, peak_time - 10),
                    end_time=min(segmenter.clip.duration, peak_time + 5),
                    score=score,
                    label=label
                )
            
            job.status = ProcessingJob.Status.SUCCEEDED
            job.progress = 100
            job.output_file = output_path 
            job.save()
            update_job_progress(job, progress=100, step="render", message="Highlight generated successfully!")
        else:
            raise Exception("Failed to generate highlight output.")

    except Exception as exc:
        print(f"ERROR Task: {str(exc)}")
        job.status = ProcessingJob.Status.FAILED
        job.error_message = str(exc)
        job.save()
        update_job_progress(job, progress=job.progress, step=job.current_step, message=f"Error: {str(exc)}", level="error")
        raise

def build_focus_windows(audio_peaks, pre_seconds=45, post_seconds=12, min_score=0.70, max_windows=10):
    windows = []
    for peak_time, score in audio_peaks[:max_windows]:
        if score < min_score:
            continue
        start = max(0, peak_time - pre_seconds)
        end = peak_time + post_seconds
        windows.append((start, end))
    if not windows:
        return []
    windows.sort(key=lambda w: w[0])
    merged = [list(windows[0])]
    for start, end in windows[1:]:
        if start <= merged[-1][1] + 2:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(s, e) for s, e in merged]

def merge_peaks(audio_peaks, vision_peaks, tolerance=5.0):
    """
    Fusionne les pics audio et visuels.
    audio_peaks: list of (time, score)
    vision_peaks: list of (time, score, label)
    """
    merged = []
    
    # On commence par ajouter tous les pics visuels (souvent plus précis sur le type d'action)
    goal_audio_threshold = 0.80
    big_chance_threshold = 0.65

    for v_time, v_score, v_label in vision_peaks:
        # Chercher s'il y a un pic audio proche pour booster le score
        boost = 0
        best_audio = None
        for a_time, a_score in audio_peaks:
            if abs(a_time - v_time) < tolerance:
                boost = a_score * 0.5
                best_audio = a_score
                break
        label = v_label
        if best_audio is not None:
            label_upper = str(label).upper()
            if best_audio >= goal_audio_threshold and (
                "TIR CADRE" in label_upper or "OCCASION" in label_upper or "TIR NON CADRE" in label_upper
            ):
                label = "BUT"
                boost += 1.5
            elif best_audio >= big_chance_threshold and "TIR CADRE" in label_upper:
                boost += 0.6
            elif best_audio >= big_chance_threshold and "OCCASION" in label_upper:
                boost += 0.4
        merged.append((v_time, v_score + boost, label))
    
    # Puis on ajoute les pics audio qui n'ont pas ete "captes" par la vision
    for a_time, a_score in audio_peaks:
        is_covered = False
        for v_time, _, _ in vision_peaks:
            if abs(a_time - v_time) < tolerance:
                is_covered = True
                break
        if not is_covered:
            label = "EXCITATION SONORE"
            score = a_score
            if a_score >= goal_audio_threshold:
                label = "BUT (AUDIO)"
                score = 4.2 + a_score
            elif a_score >= big_chance_threshold:
                label = "OCCASION (AUDIO)"
                score = 2.2 + a_score
            merged.append((a_time, score, label))
    # Tri par temps
    merged.sort(key=lambda x: x[0])
    return merged

