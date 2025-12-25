from moviepy.editor import VideoFileClip, concatenate_videoclips
import os

class VideoSegmenter:
    def __init__(self, video_path):
        self.video_path = video_path
        self.clip = VideoFileClip(video_path)

    def create_highlights(self, peaks, target_duration_mins=5):
        """
        Crée une vidéo finale à partir des pics détectés.
        peaks: liste de tuples (seconde, score, [label])
        """
        selected_segments = []
        target_seconds = target_duration_mins * 60
        current_total = 0
        
        # Fenêtre autour de chaque pic
        # Fenêtres élargies pour voir la construction de l'action
        window_before = 15 # Par défaut 15s avant
        window_after = 7   # Par défaut 7s après
        
        print(f"DEBUG Segmenter: Analyse de {len(peaks)} pics potentiels pour un total de {target_seconds}s.")

        # On trie par score pour prendre les MEILLEURES actions d'abord
        # Même si on dépasse le temps, on veut les actions à gros score
        sorted_peaks = sorted(peaks, key=lambda x: x[1], reverse=True)

        for peak_data in sorted_peaks:
            peak_time = peak_data[0]
            score = peak_data[1]
            
            # Ajustement de la fenêtre selon le type d'évènement si présent
            before = window_before
            after = window_after
            if len(peak_data) > 2:
                label = str(peak_data[2]).upper()
                if "TRANSITION" in label or "REPLAY" in label:
                    before, after = 3, 3
                elif "BUT" in label:
                    before, after = 50, 12
                elif "TIR CADRE" in label or "OCCASION" in label:
                    before, after = 22, 8
                elif "TIR NON CADRE" in label:
                    before, after = 18, 6
                elif "CORNER" in label:
                    before, after = 14, 8
                elif "CENTRE" in label or "PASS OFFENSIVE" in label:
                    before, after = 12, 6
                elif "ATTAQUE" in label:
                    before, after = 14, 6
            
            start = max(0, peak_time - before)
            video_duration = self.clip.duration
            end = min(video_duration, peak_time + after)
            
            duration = end - start
            
            # Vérification de chevauchement
            overlap = False
            for s_start, s_end in selected_segments:
                if not (end < s_start or start > s_end):
                    overlap = True
                    break
            
            if overlap:
                continue

            if current_total + duration > target_seconds:
                # Si on est déjà proche du temps cible, on arrête
                if current_total > target_seconds * 1.0:
                    break
                continue
                
            selected_segments.append((start, end))
            current_total += duration
            
        if not selected_segments:
            print("DEBUG Segmenter: Aucun segment n'a pu être sélectionné.")
            return None

        # IMPORTANT: Trier les segments par temps de début pour garder la chronologie
        selected_segments.sort(key=lambda x: x[0])
        
        print(f"DEBUG Segmenter: Montage de {len(selected_segments)} segments (Total: {current_total:.1f}s).")
        
        # Correction pour moviepy 1.0.3 (subclipped -> subclip selon version, mais ici on semble être en 1.0.3)
        # En fait moviepy 1.0.3 utilise subclip. subclipped est apparu plus tard ou est une erreur.
        # Vérifions requirements.txt : moviepy==1.0.3
        clips = []
        for s, e in selected_segments:
            try:
                # En 1.0.3 c'est subclip
                clips.append(self.clip.subclip(s, e))
            except AttributeError:
                # Au cas où
                clips.append(self.clip.subclipped(s, e))
        
        final_clip = concatenate_videoclips(clips, method="compose")
        
        output_path = "output_highlight.mp4"
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=self.clip.fps, threads=4, preset="ultrafast")
        
        return output_path

    def close(self):
        self.clip.close()

