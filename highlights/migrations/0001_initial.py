import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Project",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("processing", "Processing"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="ProcessingJob",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "current_step",
                    models.CharField(
                        blank=True,
                        default="",
                        choices=[
                            ("ingestion", "Ingestion"),
                            ("segmentation", "Segmentation"),
                            ("event_detection", "Event Detection"),
                            ("selection", "Selection"),
                            ("render", "Render"),
                        ],
                        max_length=32,
                    ),
                ),
                ("progress", models.PositiveSmallIntegerField(default=0)),
                ("target_duration_minutes", models.PositiveSmallIntegerField(default=5)),
                (
                    "output_file",
                    models.FileField(
                        blank=True, null=True, upload_to="outputs/%Y/%m/%d/"
                    ),
                ),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True, default="")),
                ("celery_task_id", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="jobs",
                        to="highlights.project",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="VideoAsset",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("file", models.FileField(upload_to="uploads/%Y/%m/%d/")),
                ("original_filename", models.CharField(max_length=255)),
                ("duration_seconds", models.FloatField(blank=True, null=True)),
                (
                    "proxy_file",
                    models.FileField(
                        blank=True, null=True, upload_to="proxies/%Y/%m/%d/"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="videos",
                        to="highlights.project",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Segment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("start_time", models.FloatField()),
                ("end_time", models.FloatField()),
                ("score", models.FloatField(default=0.0)),
                ("selected", models.BooleanField(default=False)),
                (
                    "thumbnail",
                    models.ImageField(
                        blank=True, null=True, upload_to="thumbnails/%Y/%m/%d/"
                    ),
                ),
                (
                    "preview_gif",
                    models.FileField(
                        blank=True, null=True, upload_to="previews/%Y/%m/%d/"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="segments",
                        to="highlights.processingjob",
                    ),
                ),
            ],
            options={"ordering": ["start_time"]},
        ),
        migrations.CreateModel(
            name="EventLog",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "level",
                    models.CharField(
                        choices=[
                            ("info", "Info"),
                            ("warning", "Warning"),
                            ("error", "Error"),
                        ],
                        max_length=10,
                    ),
                ),
                ("message", models.TextField()),
                ("payload", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="highlights.processingjob",
                    ),
                ),
            ],
        ),
    ]
