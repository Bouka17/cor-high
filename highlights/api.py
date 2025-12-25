from pathlib import Path

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import EventLog, ProcessingJob, Project, Segment, VideoAsset
from .serializers import (
    EventLogSerializer,
    ProcessingJobSerializer,
    ProjectSerializer,
    SegmentSerializer,
)
from .tasks import process_video_job


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().order_by("-created_at")
    serializer_class = ProjectSerializer

    def create(self, request, *args, **kwargs):
        title = request.data.get("title")
        file = request.FILES.get("file")
        if not title or not file:
            return Response(
                {"detail": "title and file are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        extension = Path(file.name).suffix.lower()
        if extension not in (".mp4", ".mov"):
            return Response(
                {"detail": "Only MP4 or MOV files are supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        project = Project.objects.create(title=title, status=Project.Status.DRAFT)
        VideoAsset.objects.create(
            project=project, file=file, original_filename=file.name
        )
        serializer = self.get_serializer(project)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        project = self.get_object()
        duration = int(request.data.get("target_duration_minutes", 7))
        destination = request.data.get("output_destination", "")
        
        job = ProcessingJob.objects.create(
            project=project, 
            target_duration_minutes=duration,
            output_destination=destination
        )
        async_result = process_video_job.delay(str(job.id))
        job.celery_task_id = async_result.id or ""
        job.save(update_fields=["celery_task_id"])
        serializer = ProcessingJobSerializer(job)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProcessingJobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProcessingJob.objects.select_related("project").order_by("-created_at")
    serializer_class = ProcessingJobSerializer


class SegmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Segment.objects.select_related("job").order_by("start_time")
    serializer_class = SegmentSerializer


class EventLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EventLog.objects.select_related("job").order_by("-created_at")
    serializer_class = EventLogSerializer
