from moviepy import VideoFileClip, concatenate_videoclips
import os

class VideoSegmenter:
    def __init__(self, video_path):
        self.video_path = video_path
        self.clip = VideoFileClip(video_path)

    def create_highlights(self, peaks, target_duration_mins=5):
        """
        Crée une vidéo finale à partir des pics détectés.
        peaks: liste de tuples (seconde, energy) triée par importance.
        """
        selected_segments = []
        target_seconds = target_duration_mins * 60
        current_total = 0
        
        # Fenêtre autour de chaque pic
        window_before = 10
        window_after = 5
        
        print(f"DEBUG Segmenter: Analyse de {len(peaks)} pics potentiels pour un total de {target_seconds}s.")

        for peak_time, energy in peaks:
            start = max(0, peak_time - window_before)
            # On s'assure de ne pas dépasser la fin de la vidéo
            video_duration = self.clip.duration
            end = min(video_duration, peak_time + window_after)
            
            duration = end - start
            
            # Vérification de chevauchement avec les segments déjà sélectionnés
            overlap = False
            for s_start, s_end in selected_segments:
                if not (end < s_start or start > s_end):
                    overlap = True
                    break
            
            if overlap:
                continue

            if current_total + duration > target_seconds:
                # Si le prochain segment dépasse le temps, on continue pour voir s'il y en a un plus court
                # ou on arrête si on est proche de la cible.
                if current_total > target_seconds * 0.9:
                    break
                continue
                
            selected_segments.append((start, end))
            current_total += duration
            
        if not selected_segments:
            print("DEBUG Segmenter: Aucun segment n'a pu être sélectionné.")
            return None

        # IMPORTANT: Trier les segments par temps de début pour garder la chronologie du match
        selected_segments.sort(key=lambda x: x[0])
        
        print(f"DEBUG Segmenter: Montage de {len(selected_segments)} segments (Total: {current_total:.1f}s).")
        
        clips = [self.clip.subclipped(s, e) for s, e in selected_segments]
        final_clip = concatenate_videoclips(clips, method="compose")
        
        output_path = "output_highlight.mp4"
        # Utilisation de preset 'ultrafast' pour le dev, threading pour la vitesse
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=self.clip.fps)
        
        return output_path

    def close(self):
        self.clip.close()
