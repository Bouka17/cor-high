from django.contrib import admin

from .models import EventLog, ProcessingJob, Project, Segment, VideoAsset


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "created_at")
    search_fields = ("title",)


@admin.register(VideoAsset)
class VideoAssetAdmin(admin.ModelAdmin):
    list_display = ("project", "original_filename", "created_at")
    search_fields = ("original_filename",)


@admin.register(ProcessingJob)
class ProcessingJobAdmin(admin.ModelAdmin):
    list_display = ("project", "status", "current_step", "progress", "created_at")
    list_filter = ("status", "current_step")


@admin.register(Segment)
class SegmentAdmin(admin.ModelAdmin):
    list_display = ("job", "start_time", "end_time", "label", "score", "selected")
    list_filter = ("selected", "label")


@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    list_display = ("job", "level", "message", "created_at")
    list_filter = ("level",)
