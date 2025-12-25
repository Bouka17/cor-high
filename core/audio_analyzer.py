import numpy as np
import librosa
from moviepy import VideoFileClip
import os

class AudioAnalyzer:
    def __init__(self, video_path):
        self.video_path = video_path
        self.audio_path = "temp_audio.wav"

    def extract_audio(self):
        """Désormais géré directement par librosa pour plus de vitesse."""
        print(f"DEBUG Audio: Extraction non nécessaire, librosa va lire {self.video_path}")
        return self.video_path

    def get_excitement_peaks(self, threshold_factor=1.5, min_distance_sec=15):
        """
        Analyse l'amplitude audio pour trouver les pics de 'commotion' (buts/foules).
        Retourne une liste de tuples (time, energy) triée par énergie décroissante.
        """
        print(f"DEBUG Audio: Chargement du fichier (cela peut être long)...")
        try:
            # On charge en mono pour l'analyse d'énergie
            y, sr = librosa.load(self.video_path, sr=22050, mono=True)
        except Exception as e:
            print(f"DEBUG Audio Error: {e}")
            raise e
        
        print(f"DEBUG Audio: Analyse RMS...")
        # Hop length plus grand pour lisser un peu
        hop_length = 512
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        times = librosa.frames_to_time(range(len(rms)), sr=sr, hop_length=hop_length)
        
        # Normalisation pour faciliter le seuillage
        if np.max(rms) > 0:
            rms = rms / np.max(rms)

        # On utilise le 70ème percentile comme base plutôt que la moyenne simple
        base_threshold = np.percentile(rms, 70)
        threshold = base_threshold * threshold_factor
        
        raw_peaks = []
        for i in range(1, len(rms) - 1):
            if rms[i] > threshold and rms[i] > rms[i-1] and rms[i] > rms[i+1]:
                raw_peaks.append((times[i], rms[i]))
        
        # Filtrage par distance minimum pour éviter les doublons sur une même action
        peaks = []
        if raw_peaks:
            # On trie d'abord par temps pour le filtrage de proximité
            raw_peaks.sort(key=lambda x: x[0])
            
            for p_time, p_energy in raw_peaks:
                if not peaks or (p_time - peaks[-1][0] > min_distance_sec):
                    peaks.append((p_time, p_energy))
        
        # On retourne les pics triés par ÉNERGIE (les plus forts d'abord)
        peaks.sort(key=lambda x: x[1], reverse=True)
        
        print(f"DEBUG Audio: {len(peaks)} pics détectés (filtrés).")
        return peaks
