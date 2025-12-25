from pathlib import Path

from .ffmpeg import run_ffmpeg


def create_proxy(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    args = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vf",
        "scale=1280:-2",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "28",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        str(output_path),
    ]
    run_ffmpeg(args)
