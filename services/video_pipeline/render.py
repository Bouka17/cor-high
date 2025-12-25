from pathlib import Path

from .ffmpeg import run_ffmpeg
from .types import SelectedSegment


def render_highlight(
    video_path: Path, segments: list[SelectedSegment], output_path: Path, work_dir: Path
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    clips_dir = work_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    clip_paths: list[Path] = []
    for index, segment in enumerate(segments):
        clip_path = clips_dir / f"clip_{index:03d}.mp4"
        duration = segment.end - segment.start
        args = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{segment.start:.2f}",
            "-i",
            str(video_path),
            "-t",
            f"{duration:.2f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            str(clip_path),
        ]
        run_ffmpeg(args)
        clip_paths.append(clip_path)

    concat_list = work_dir / "concat.txt"
    with open(concat_list, "w", encoding="utf-8") as handle:
        for clip_path in clip_paths:
            handle.write(f"file '{clip_path.as_posix()}'\n")

    args = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_list),
        "-c",
        "copy",
        str(output_path),
    ]
    run_ffmpeg(args)
