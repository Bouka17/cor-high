from pathlib import Path
import subprocess
import re

import cv2

from .types import ScoredSegment, SegmentSpec


def compute_motion_scores(
    video_path: Path, segments: list[SegmentSpec], sample_fps: float = 1.0
) -> list[float]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError("Unable to open video for motion scoring.")
    scores: list[float] = []
    for segment in segments:
        start_ms = segment.start * 1000
        end_ms = segment.end * 1000
        cap.set(cv2.CAP_PROP_POS_MSEC, start_ms)
        prev_gray = None
        motion_values: list[float] = []
        current_ms = start_ms
        step_ms = 1000 / sample_fps
        while current_ms < end_ms:
            success, frame = cap.read()
            if not success:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                diff = cv2.absdiff(gray, prev_gray)
                motion_values.append(float(diff.mean()))
            prev_gray = gray
            current_ms += step_ms
            cap.set(cv2.CAP_PROP_POS_MSEC, current_ms)
        scores.append(sum(motion_values) / len(motion_values) if motion_values else 0.0)
    cap.release()
    return scores


def compute_audio_scores(video_path: Path, segments: list[SegmentSpec]) -> list[float]:
    """
    Computes audio energy scores for each segment using ffprobe's volumedetect filter.
    Returns a list of normalized scores (0.0 to 1.0).
    """
    scores: list[float] = []
    for segment in segments:
        duration = segment.end - segment.start
        # We use a short snippet to get the mean volume
        args = [
            "ffmpeg",
            "-ss", str(segment.start),
            "-t", str(duration),
            "-i", str(video_path),
            "-af", "volumedetect",
            "-f", "null",
            "-"
        ]
        completed = subprocess.run(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False
        )
        # Search for mean_volume in the output
        import re
        match = re.search(r"mean_volume: ([\-\d\.]+) dB", completed.stderr)
        if match:
            # Volume is usually negative (e.g. -20dB). Higher (less negative) is louder.
            # Typical range is -60 to 0.
            db = float(match.group(1))
            normalized = max(0.0, min(1.0, (db + 60) / 60))
            scores.append(normalized)
        else:
            scores.append(0.5)
    return scores


def score_segments(
    video_path: Path, segments: list[SegmentSpec]
) -> list[ScoredSegment]:
    motion_scores = compute_motion_scores(video_path, segments)
    audio_scores = compute_audio_scores(video_path, segments)
    max_motion = max(motion_scores) if motion_scores else 1.0
    if max_motion == 0:
        max_motion = 1.0
    scored: list[ScoredSegment] = []
    for segment, motion, audio in zip(segments, motion_scores, audio_scores):
        normalized_motion = motion / max_motion
        total_score = 0.7 * normalized_motion + 0.3 * audio
        scored.append(
            ScoredSegment(
                start=segment.start,
                end=segment.end,
                motion_score=normalized_motion,
                audio_score=audio,
                total_score=total_score,
            )
        )
    return scored
