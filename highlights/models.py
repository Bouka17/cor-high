import uuid

from django.db import models


class Project(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title


class VideoAsset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="videos"
    )
    file = models.FileField(upload_to="uploads/%Y/%m/%d/")
    original_filename = models.CharField(max_length=255)
    duration_seconds = models.FloatField(null=True, blank=True)
    proxy_file = models.FileField(upload_to="proxies/%Y/%m/%d/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.project.title} ({self.original_filename})"


class ProcessingJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    class Step(models.TextChoices):
        INGESTION = "ingestion", "Ingestion"
        SEGMENTATION = "segmentation", "Segmentation"
        EVENT_DETECTION = "event_detection", "Event Detection"
        SELECTION = "selection", "Selection"
        RENDER = "render", "Render"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="jobs"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    current_step = models.CharField(
        max_length=32, choices=Step.choices, blank=True, default=""
    )
    progress = models.PositiveSmallIntegerField(default=0)
    target_duration_minutes = models.PositiveSmallIntegerField(default=5)
    output_file = models.FileField(
        upload_to="outputs/%Y/%m/%d/", null=True, blank=True
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    celery_task_id = models.CharField(max_length=255, blank=True, default="")
    output_destination = models.CharField(max_length=512, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Job {self.id} ({self.project.title})"


class Segment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        ProcessingJob, on_delete=models.CASCADE, related_name="segments"
    )
    start_time = models.FloatField()
    end_time = models.FloatField()
    score = models.FloatField(default=0.0)
    label = models.CharField(max_length=100, blank=True, default="Action")
    selected = models.BooleanField(default=False)
    thumbnail = models.ImageField(
        upload_to="thumbnails/%Y/%m/%d/", null=True, blank=True
    )
    preview_gif = models.FileField(
        upload_to="previews/%Y/%m/%d/", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_time"]

    def __str__(self) -> str:
        return f"{self.start_time:.2f}-{self.end_time:.2f}s"


class EventLog(models.Model):
    class Level(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        ProcessingJob, on_delete=models.CASCADE, related_name="events"
    )
    level = models.CharField(max_length=10, choices=Level.choices)
    message = models.TextField()
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.level.upper()} - {self.message[:50]}"
