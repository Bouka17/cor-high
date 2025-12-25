from pathlib import Path

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
import os
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

    @action(detail=False, methods=["post"])
    def select_folder(self, request):
        """Ouvre un dialogue de sélection de dossier natif sur le serveur (Windows)."""
        try:
            import tkinter as tk
            from tkinter import filedialog
            
            # Check if we have a display
            if os.environ.get('DISPLAY') == '' and os.name != 'nt':
                 return Response({"error": "No display available"}, status=status.HTTP_400_BAD_REQUEST)

            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            folder_path = filedialog.askdirectory()
            root.destroy()
            
            if folder_path:
                # Normalisation pour Windows
                folder_path = os.path.abspath(folder_path)
                return Response({"path": folder_path})
            return Response({"path": ""})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProcessingJobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProcessingJob.objects.select_related("project").order_by("-created_at")
    serializer_class = ProcessingJobSerializer

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        from cortexm_highlights.celery import app
        job = self.get_object()
        if job.celery_task_id:
            app.control.revoke(job.celery_task_id, terminate=True)
        job.status = ProcessingJob.Status.FAILED
        job.error_message = "Cancelled by user"
        job.save()
        return Response({"status": "cancelled"})


class SegmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Segment.objects.select_related("job").order_by("start_time")
    serializer_class = SegmentSerializer


class EventLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EventLog.objects.select_related("job").order_by("-created_at")
    serializer_class = EventLogSerializer
