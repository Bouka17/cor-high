from pathlib import Path

from .ffmpeg import run_ffmpeg


def generate_thumbnail(video_path: Path, output_path: Path, timestamp_seconds: float) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    args = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{timestamp_seconds:.2f}",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(output_path),
    ]
    run_ffmpeg(args)
