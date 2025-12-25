from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.views import View

from .forms import ProcessingJobForm, ProjectUploadForm
from .models import ProcessingJob, Project, VideoAsset
from .tasks import process_video_job


def index(request):
    return render(request, 'index.html')


class UploadView(View):
    template_name = "highlights/upload.html"

    def get(self, request):
        return render(request, self.template_name, {"form": ProjectUploadForm()})

    def post(self, request):
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
        form = ProjectUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            if is_ajax:
                error_data = {
                    field: [str(err) for err in errors]
                    for field, errors in form.errors.items()
                }
                return JsonResponse(
                    {"error": "Validation error.", "details": error_data},
                    status=400,
                )
            return render(request, self.template_name, {"form": form})

        try:
            project = Project.objects.create(title=form.cleaned_data["title"])
            upload = form.cleaned_data["file"]
            VideoAsset.objects.create(
                project=project, file=upload, original_filename=upload.name
            )
        except Exception as exc:
            message = f"Upload failed: {exc}"
            if is_ajax:
                return JsonResponse({"error": message}, status=500)
            return render(
                request,
                self.template_name,
                {"form": form, "upload_error": message},
                status=500,
            )
        redirect_url = reverse("project_start", kwargs={"project_id": project.id})
        if is_ajax:
            return JsonResponse({"redirect_url": redirect_url})
        return redirect(redirect_url)


class ProjectStartView(View):
    template_name = "highlights/project_start.html"

    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        latest_job = project.jobs.order_by("-created_at").first()
        if latest_job and latest_job.status in (
            ProcessingJob.Status.PENDING,
            ProcessingJob.Status.RUNNING,
        ):
            return redirect("job_progress", job_id=latest_job.id)
        return render(
            request,
            self.template_name,
            {"project": project, "form": ProcessingJobForm()},
        )

    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        form = ProcessingJobForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"project": project, "form": form},
            )
        duration = int(form.cleaned_data["target_duration_minutes"])
        job = ProcessingJob.objects.create(
            project=project, target_duration_minutes=duration
        )
        async_result = process_video_job.delay(str(job.id))
        job.celery_task_id = async_result.id or ""
        job.save(update_fields=["celery_task_id"])
        return redirect("job_progress", job_id=job.id)


class JobProgressView(View):
    template_name = "highlights/job_progress.html"

    def get(self, request, job_id):
        job = get_object_or_404(ProcessingJob, id=job_id)
        if job.status == ProcessingJob.Status.FAILED:
            return redirect("job_failed", job_id=job.id)
        if job.status == ProcessingJob.Status.SUCCEEDED:
            return redirect("job_result", job_id=job.id)
        segments = job.segments.filter(selected=True).order_by("start_time")
        return render(
            request,
            self.template_name,
            {"job": job, "segments": segments},
        )


class JobResultView(View):
    template_name = "highlights/job_result.html"

    def get(self, request, job_id):
        job = get_object_or_404(ProcessingJob, id=job_id)
        if job.status == ProcessingJob.Status.FAILED:
            return redirect("job_failed", job_id=job.id)
        if job.status != ProcessingJob.Status.SUCCEEDED:
            return redirect("job_progress", job_id=job.id)
        return render(request, self.template_name, {"job": job})


class JobFailedView(View):
    template_name = "highlights/job_failed.html"

    def get(self, request, job_id):
        job = get_object_or_404(ProcessingJob, id=job_id)
        events = job.events.order_by("-created_at")[:10]
        return render(
            request,
            self.template_name,
            {"job": job, "events": events},
        )


class JobStatusPartialView(View):
    template_name = "highlights/_job_status.html"

    def get(self, request, job_id):
        job = get_object_or_404(ProcessingJob, id=job_id)
        return render(request, self.template_name, {"job": job})
@csrf_exempt
def browse_folder(request):
    import tkinter as tk
    from tkinter import filedialog
    import os

    root = tk.Tk()
    root.withdraw()  # Hide the main tkinter window
    root.attributes('-topmost', True)  # Bring the dialog to the front
    
    folder_selected = filedialog.askdirectory()
    root.destroy()
    
    if folder_selected:
        # Normalize path for Windows
        folder_selected = os.path.normpath(folder_selected)
        return JsonResponse({"path": folder_selected})
    return JsonResponse({"path": ""})
