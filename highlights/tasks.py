from celery import shared_task
from django.utils import timezone

from .models import ProcessingJob, Project


@shared_task(bind=True, max_retries=3)
def process_video_job(self, job_id: str) -> None:
    from core.audio_analyzer import AudioAnalyzer
    from core.video_segmenter import VideoSegmenter
    from .models import ProcessingJob, VideoAsset, Segment
    from services.video_pipeline.progress import update_job_progress
    import os

    print(f"DEBUG Task: Lancement pour le job {job_id}")
    job = ProcessingJob.objects.select_related("project").get(id=job_id)
    video_asset = VideoAsset.objects.get(project=job.project)
    video_path = video_asset.file.path
    print(f"DEBUG Task: Chemin vidéo trouvé: {video_path}")

    try:
        # Step 1: Extract & Analyze Audio
        print("DEBUG Task: Étape 1 - Analyse Audio...")
        update_job_progress(job, progress=10, step="event_detection", message="Analyse sonore du match...")
        analyzer = AudioAnalyzer(video_path)
        # extract_audio ne fait plus rien de lourd maintenant
        analyzer.extract_audio()
        
        print("DEBUG Task: Détection des pics d'excitation...")
        peaks = analyzer.get_excitement_peaks()
        print(f"DEBUG Task: {len(peaks)} temps forts détectés.")
        
        # Step 2: Segment Video
        print("DEBUG Task: Étape 2 - Montage Vidéo...")
        update_job_progress(job, progress=50, step="render", message="Création du montage (cela peut être long)...")
        segmenter = VideoSegmenter(video_path)
        output_path = segmenter.create_highlights(peaks, target_duration_mins=job.target_duration_minutes)
        print(f"DEBUG Task: Montage terminé -> {output_path}")
        
        # Step 3: Finalize
        if output_path and os.path.exists(output_path):
            # If a custom destination is provided, move the file there
            if job.output_destination:
                dest_dir = os.path.dirname(job.output_destination)
                if dest_dir and not os.path.exists(dest_dir):
                    os.makedirs(dest_dir, exist_ok=True)
                
                # If destination is a directory, append filename
                if os.path.isdir(job.output_destination) or not os.path.splitext(job.output_destination)[1]:
                    final_path = os.path.join(job.output_destination, "highlight_" + job.project.title)
                    if not final_path.endswith(".mp4"): final_path += ".mp4"
                else:
                    final_path = job.output_destination
                
                import shutil
                shutil.move(output_path, final_path)
                output_path = final_path

        # Save segments to database for the preview grid
            for peak_time, energy in peaks:
                Segment.objects.create(
                    job=job,
                    start_time=max(0, peak_time-10),
                    end_time=min(segmenter.clip.duration, peak_time+5),
                    score=energy
                )
            
            job.status = ProcessingJob.Status.SUCCEEDED
            job.progress = 100
            # In a real app, we would move the output file to media storage
            job.output_file = output_path 
            job.save()
            update_job_progress(job, progress=100, step="render", message="Highlight generated successfully!")
        else:
            raise Exception("Failed to generate highlight output.")

    except Exception as exc:
        job.status = ProcessingJob.Status.FAILED
        job.error_message = str(exc)
        job.save()
        update_job_progress(job, progress=job.progress, step=job.current_step, message=f"Error: {str(exc)}", level="error")
        raise
