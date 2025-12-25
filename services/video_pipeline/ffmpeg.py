import subprocess
from pathlib import Path


def run_ffmpeg(args: list[str]) -> None:
    completed = subprocess.run(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed ({completed.returncode}): {completed.stderr.strip()}"
        )


def probe_duration_seconds(video_path: Path) -> float:
    args = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    completed = subprocess.run(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed ({completed.returncode}): {completed.stderr.strip()}"
        )
    return float(completed.stdout.strip())
