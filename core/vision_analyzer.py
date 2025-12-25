import cv2
import numpy as np
from ultralytics import YOLO
import torch
import os

class VisionAnalyzer:
    def __init__(self, video_path):
        self.video_path = video_path
        # Utilisation de YOLOv8n (nano) pour la rapidité
        self.model = YOLO('yolov8n.pt') 
        self.cap = cv2.VideoCapture(video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.duration = self.total_frames / self.fps if self.fps > 0 else 0
        self.last_shot_time = None
        self.last_shot_on_target_time = None

    def analyze_events(self, sample_rate=1.0, focus_windows=None, focus_sample_rate=2.5):
        """Analyse la vidéo avec optimisation de skip (grab) et batching."""
        focus_windows = focus_windows or []
        if focus_windows:
            print(f"DEBUG Vision: Analyse optimisee {sample_rate} fps (focus {focus_sample_rate} fps sur {len(focus_windows)} zones)")
        else:
            print(f"DEBUG Vision: Analyse optimisee de {self.video_path} ({sample_rate} fps)")
        
        # Détection GPU
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        if device == 'cuda':
            self.model.to(device)
            # self.model.model.half() # Optionnel pour GPU supportant FP16
            print("DEBUG Vision: Utilisation du GPU pour YOLO.")
        
        events = []
        # Calcul du pas de frame
        frame_step_base = max(1, int(self.fps / sample_rate)) if self.fps > 0 else 30
        frame_step_focus = frame_step_base
        if focus_windows:
            frame_step_focus = max(1, int(self.fps / focus_sample_rate)) if self.fps > 0 else 30
        
        ball_history = []
        prev_frame_gray = None
        count = 0
        processed_frames = 0
        
        # Batching pour accélérer l'inférence
        batch_size = 12 if device == 'cuda' else 4
        frames_batch = []
        times_batch = []
        
        while True:
            current_ts = count / self.fps if self.fps > 0 else 0
            in_focus = False
            if focus_windows:
                for w_start, w_end in focus_windows:
                    if w_start <= current_ts <= w_end:
                        in_focus = True
                        break
            step = frame_step_focus if in_focus else frame_step_base
            # OPTIMISATION FAST SKIP : grab() ne décompresse pas la frame
            for _ in range(step - 1):
                if not self.cap.grab(): break
            
            ret, frame = self.cap.read()
            if not ret: break
            
            timestamp = count / self.fps
            
            # OPTIMISATION RESIZE : Inférence sur une petite résolution
            # YOLOv8n gère très bien le 320x320 pour les joueurs/balles
            # OPTIMISATION : Inférence en 640p pour une détection précise du ballon
            h, w = frame.shape[:2]
            target_h = 640
            scale = target_h / h
            target_w = int(w * scale)
            small_frame = cv2.resize(frame, (target_w, target_h))
            
            frames_batch.append(small_frame)
            times_batch.append(timestamp)
            
            if len(frames_batch) >= batch_size:
                self._process_batch(frames_batch, times_batch, events, ball_history, prev_frame_gray, target_w, target_h)
                # On met à jour le frame gray de référence (dernier du batch)
                prev_frame_gray = cv2.cvtColor(frames_batch[-1], cv2.COLOR_BGR2GRAY)
                frames_batch = []
                times_batch = []

            count += step
            processed_frames += 1
            if processed_frames % 50 == 0:
                print(f"DEBUG Vision: {int(timestamp/60)}min traitees...")

        # Dernier batch
        if frames_batch:
            self._process_batch(frames_batch, times_batch, events, ball_history, prev_frame_gray, target_w, target_h)
            
        return self.group_events(events)

    def _process_batch(self, frames, timestamps, events, ball_history, prev_gray, w, h):
        """Inférence groupée et heuristiques haute précision."""
        # imgsz=640 pour ne rater aucun petit objet (ballon)
        results = self.model(frames, verbose=False, conf=0.15, imgsz=640)
        
        for i, res in enumerate(results):
            ts = timestamps[i]
            detections = res.boxes.data.cpu().numpy()

            players = [d for d in detections if int(d[5]) == 0]
            balls = [d for d in detections if int(d[5]) == 32]

            score = 0.0
            label = "Action"
            priority = 0

            player_count = len(players)
            cluster_tight = False
            if player_count > 9:
                pxs = [p[0] for p in players]
                pys = [p[1] for p in players]
                spread = (max(pxs) - min(pxs)) * (max(pys) - min(pys))
                if spread < (w * h * 0.35):
                    cluster_tight = True
                    label = "REGROUPEMENT"
                    score = 0.9
                    priority = 1

            ball_center = None
            dx = 0.0
            dy = 0.0
            dist_ratio = 0.0
            speed_ratio = 0.0
            moving_toward_goal = False
            in_goal_zone = False
            in_box_zone = False
            in_final_third = False
            in_corner = False
            in_goal_band = False

            if balls:
                ball = max(balls, key=lambda b: b[4])
                ball_box = ball[:4]
                ball_center = (
                    (ball_box[0] + ball_box[2]) / 2,
                    (ball_box[1] + ball_box[3]) / 2,
                )
                ball_history.append((ball_center[0], ball_center[1], ts))
                if len(ball_history) > 6:
                    ball_history.pop(0)

                if len(ball_history) >= 2:
                    prev_x, prev_y, prev_ts = ball_history[-2]
                    dx = ball_center[0] - prev_x
                    dy = ball_center[1] - prev_y
                    dist = np.sqrt(dx * dx + dy * dy)
                    dt = max(ts - prev_ts, 1.0 / max(self.fps, 1))
                    dist_ratio = dist / max(w, 1)
                    speed_ratio = (dist / dt) / max(w, 1)
                    goal_dir = -1 if ball_center[0] < (w / 2) else 1
                    moving_toward_goal = (dx * goal_dir) > 0 and abs(dx) > abs(dy) * 0.6

                in_goal_zone = ball_center[0] < w * 0.15 or ball_center[0] > w * 0.85
                in_box_zone = ball_center[0] < w * 0.22 or ball_center[0] > w * 0.78
                in_final_third = ball_center[0] < w * 0.33 or ball_center[0] > w * 0.67
                in_corner = (
                    (ball_center[0] < w * 0.08 or ball_center[0] > w * 0.92)
                    and (ball_center[1] < h * 0.12 or ball_center[1] > h * 0.88)
                )
                in_goal_band = (h * 0.2) <= ball_center[1] <= (h * 0.8)

                fast_move = speed_ratio > 0.22 and dist_ratio > 0.035
                medium_move = speed_ratio > 0.10 and dist_ratio > 0.018
                shot_candidate = in_final_third and moving_toward_goal and (fast_move or medium_move)

                if fast_move and priority < 2:
                    label = "ACTION RAPIDE"
                    score = 1.2
                    priority = 2

                if in_final_third and medium_move and moving_toward_goal and priority < 4:
                    label = "PASS OFFENSIVE"
                    score = 1.6
                    priority = 4

                if in_final_third and medium_move and abs(dy) > abs(dx) * 1.2 and priority < 4:
                    label = "CENTRE"
                    score = 1.7
                    priority = 4

                if in_final_third and player_count >= 7 and priority < 3:
                    label = "ATTAQUE"
                    score = 1.4
                    priority = 3

                if in_corner and player_count >= 7 and priority < 5:
                    label = "CORNER"
                    score = 2.1
                    priority = 5

                if in_box_zone and (player_count >= 6 or medium_move) and priority < 6:
                    label = "OCCASION"
                    score = 2.7
                    priority = 6

                if shot_candidate:
                    if in_goal_zone and in_goal_band:
                        label = "TIR CADRE"
                        score = 3.6
                        priority = 8
                        self.last_shot_on_target_time = ts
                        self.last_shot_time = ts
                        print(f"DEBUG Vision: Shot on target at {ts:.1f}s")
                    elif in_goal_zone:
                        label = "TIR NON CADRE"
                        score = 2.4
                        priority = 7
                        self.last_shot_time = ts

            if cluster_tight and self.last_shot_on_target_time is not None:
                if 0 <= (ts - self.last_shot_on_target_time) <= 10 and not in_corner:
                    label = "BUT"
                    score = max(score, 5.5)
                    priority = 10
                    self.last_shot_on_target_time = None
                    print(f"DEBUG Vision: Goal candidate at {ts:.1f}s")

            current_gray = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                diff = np.mean(cv2.absdiff(current_gray, prev_gray))
                if diff > 40 and priority < 2:
                    score = max(score, 1.2)
                    label = "TRANSITION / REPLAY"
                    priority = 2
            prev_gray = current_gray

            if score > 0.5:
                events.append({'time': ts, 'score': score, 'label': label})
    def group_events(self, raw_events, min_dist=12):
        if not raw_events: return []
        raw_events.sort(key=lambda x: x['time'])
        merged = []
        curr = raw_events[0]
        for i in range(1, len(raw_events)):
            e = raw_events[i]
            if e['time'] - curr['time'] < min_dist:
                if e['score'] > curr['score']: curr = e
            else:
                merged.append((curr['time'], curr['score'], curr['label']))
                curr = e
        merged.append((curr['time'], curr['score'], curr['label']))
        return merged

    def close(self):
        self.cap.release()