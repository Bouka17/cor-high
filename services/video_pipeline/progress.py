from typing import Iterable, Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from highlights.models import EventLog, ProcessingJob, Segment


def serialize_segment(segment: Segment) -> dict:
    return {
        "id": str(segment.id),
        "start_time": segment.start_time,
        "end_time": segment.end_time,
        "score": segment.score,
        "selected": segment.selected,
        "thumbnail_url": segment.thumbnail.url if segment.thumbnail else None,
        "preview_gif_url": segment.preview_gif.url if segment.preview_gif else None,
    }


def log_event(job: ProcessingJob, level: str, message: str, payload: dict | None = None) -> None:
    EventLog.objects.create(job=job, level=level, message=message, payload=payload)


def publish_job_update(
    job: ProcessingJob,
    message: Optional[str] = None,
    level: str = "info",
    segments: Optional[Iterable[Segment]] = None,
) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    payload = {
        "job_id": str(job.id),
        "status": job.status,
        "current_step": job.current_step,
        "progress": job.progress,
        "message": message,
        "level": level,
        "segments": [serialize_segment(seg) for seg in segments] if segments else [],
    }
    async_to_sync(channel_layer.group_send)(
        f"job_{job.id}", {"type": "job.update", "payload": payload}
    )


def update_job_progress(
    job: ProcessingJob,
    progress: int,
    step: str,
    message: Optional[str] = None,
    level: str = "info",
    segments: Optional[Iterable[Segment]] = None,
) -> None:
    job.progress = progress
    job.current_step = step
    job.save(update_fields=["progress", "current_step", "updated_at"])
    if message:
        log_event(job, level=level, message=message)
    publish_job_update(job, message=message, level=level, segments=segments)
