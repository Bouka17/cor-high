from pathlib import Path

from .ffmpeg import probe_duration_seconds
from .types import SegmentSpec


def segment_shots(video_path: Path, segment_seconds: float = 10.0) -> list[SegmentSpec]:
    duration = probe_duration_seconds(video_path)
    segments: list[SegmentSpec] = []
    start = 0.0
    while start < duration:
        end = min(start + segment_seconds, duration)
        segments.append(SegmentSpec(start=start, end=end))
        start = end
    return segments
