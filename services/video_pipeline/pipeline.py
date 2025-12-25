from pathlib import Path

from django.conf import settings
from django.utils import timezone

from highlights.models import ProcessingJob, Project, Segment, VideoAsset

from .ffmpeg import probe_duration_seconds
from .progress import log_event, publish_job_update, update_job_progress
from .render import render_highlight
from .scoring import score_segments
from .segmentation import segment_shots
from .selection import select_segments
from .storage import save_from_local, stage_to_local
from .thumbnails import generate_thumbnail
from .transcode import create_proxy


def run_pipeline(job_id) -> None:
    job = ProcessingJob.objects.select_related("project").get(id=job_id)
    project = job.project
    job.status = ProcessingJob.Status.RUNNING
    job.started_at = timezone.now()
    job.progress = 0
    job.save(update_fields=["status", "started_at", "progress"])
    Project.objects.filter(id=project.id).update(status=Project.Status.PROCESSING)
    publish_job_update(job, message="Job started")

    video = (
        VideoAsset.objects.filter(project=project).order_by("-created_at").first()
    )
    if not video:
        raise RuntimeError("No video asset found for project.")

    work_dir = Path(settings.MEDIA_ROOT) / "work" / str(job.id)
    input_suffix = Path(video.file.name).suffix or ".mp4"

    try:
        source_path = stage_to_local(video.file, work_dir, f"source{input_suffix}")
        duration = probe_duration_seconds(source_path)
        VideoAsset.objects.filter(id=video.id).update(duration_seconds=duration)

        proxy_local_path = work_dir / "proxy.mp4"
        create_proxy(source_path, proxy_local_path)
        proxy_name = save_from_local(
            proxy_local_path, f"proxies/{project.id}/proxy.mp4"
        )
        VideoAsset.objects.filter(id=video.id).update(proxy_file=proxy_name)
        update_job_progress(
            job, 20, ProcessingJob.Step.INGESTION, message="Proxy generated"
        )

        update_job_progress(
            job, 35, ProcessingJob.Step.SEGMENTATION, message="Segmenting shots"
        )
        segments = segment_shots(proxy_local_path, segment_seconds=10.0)
        if not segments:
            raise RuntimeError("No segments detected.")

        update_job_progress(
            job,
            50,
            ProcessingJob.Step.EVENT_DETECTION,
            message="Scoring segments",
        )
        scored_segments = score_segments(proxy_local_path, segments)

        update_job_progress(
            job,
            65,
            ProcessingJob.Step.SELECTION,
            message="Selecting best moments",
        )
        target_seconds = job.target_duration_minutes * 60
        selected_segments = select_segments(scored_segments, target_seconds)
        if not selected_segments:
            raise RuntimeError("No segments selected for highlight.")

        selected_keys = {(seg.start, seg.end) for seg in selected_segments}
        segment_models: list[Segment] = []
        for seg in scored_segments:
            segment_models.append(
                Segment(
                    job=job,
                    start_time=seg.start,
                    end_time=seg.end,
                    score=seg.total_score,
                    selected=(seg.start, seg.end) in selected_keys,
                )
            )
        Segment.objects.bulk_create(segment_models)

        selected_qs = Segment.objects.filter(job=job, selected=True).order_by("start_time")
        update_job_progress(
            job,
            75,
            ProcessingJob.Step.SELECTION,
            message="Generating thumbnails",
        )
        for segment in selected_qs:
            midpoint = segment.start_time + (segment.end_time - segment.start_time) / 2
            thumb_path = work_dir / "thumbnails" / f"{segment.id}.jpg"
            generate_thumbnail(proxy_local_path, thumb_path, midpoint)
            stored_name = save_from_local(
                thumb_path, f"thumbnails/{job.id}/{segment.id}.jpg"
            )
            segment.thumbnail = stored_name
            segment.save(update_fields=["thumbnail"])

        publish_job_update(job, message="Segments ready", segments=selected_qs)

        update_job_progress(
            job, 85, ProcessingJob.Step.RENDER, message="Rendering highlight"
        )
        output_local_path = work_dir / "output.mp4"
        render_highlight(proxy_local_path, selected_segments, output_local_path, work_dir)
        output_name = save_from_local(
            output_local_path, f"outputs/{job.id}/highlight.mp4"
        )
        job.output_file = output_name
        job.progress = 95
        job.current_step = ProcessingJob.Step.RENDER
        job.save(update_fields=["output_file", "progress", "current_step", "updated_at"])
        publish_job_update(job, message="Finalizing output")

        job.status = ProcessingJob.Status.SUCCEEDED
        job.progress = 100
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "progress", "finished_at", "updated_at"])
        Project.objects.filter(id=project.id).update(status=Project.Status.COMPLETED)
        log_event(job, level="info", message="Highlight generation completed.")
        publish_job_update(job, message="Highlight ready")

    except Exception as exc:
        # Error handling is partially in tasks.py, but we ensure local state here
        job.status = ProcessingJob.Status.FAILED
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message"])
        raise
    finally:
        # Cleanup temporary files
        import shutil
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)
