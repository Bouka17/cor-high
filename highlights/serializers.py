from rest_framework import serializers

from .models import EventLog, ProcessingJob, Project, Segment, VideoAsset


class VideoAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoAsset
        fields = [
            "id",
            "project",
            "file",
            "original_filename",
            "duration_seconds",
            "proxy_file",
            "created_at",
        ]


class ProjectSerializer(serializers.ModelSerializer):
    videos = VideoAssetSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ["id", "title", "status", "created_at", "updated_at", "videos"]


class ProcessingJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingJob
        fields = [
            "id",
            "project",
            "status",
            "current_step",
            "progress",
            "target_duration_minutes",
            "output_file",
            "started_at",
            "finished_at",
            "error_message",
            "created_at",
            "updated_at",
        ]


class SegmentSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()
    preview_gif_url = serializers.SerializerMethodField()

    class Meta:
        model = Segment
        fields = [
            "id",
            "job",
            "start_time",
            "end_time",
            "score",
            "label",
            "selected",
            "thumbnail_url",
            "preview_gif_url",
            "created_at",
        ]

    def get_thumbnail_url(self, obj: Segment) -> str | None:
        return obj.thumbnail.url if obj.thumbnail else None

    def get_preview_gif_url(self, obj: Segment) -> str | None:
        return obj.preview_gif.url if obj.preview_gif else None


class EventLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventLog
        fields = ["id", "job", "level", "message", "payload", "created_at"]
