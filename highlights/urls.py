from django.urls import path

from .views import (
    index,
    JobFailedView,
    JobProgressView,
    JobResultView,
    JobStatusPartialView,
    ProjectStartView,
    UploadView,
    browse_folder,
)

urlpatterns = [
    path("", index, name="index"),
    path("upload-old/", UploadView.as_view(), name="upload"),
    path("projects/<uuid:project_id>/start/", ProjectStartView.as_view(), name="project_start"),
    path("jobs/<uuid:job_id>/", JobProgressView.as_view(), name="job_progress"),
    path("jobs/<uuid:job_id>/result/", JobResultView.as_view(), name="job_result"),
    path("jobs/<uuid:job_id>/failed/", JobFailedView.as_view(), name="job_failed"),
    path("jobs/<uuid:job_id>/status/", JobStatusPartialView.as_view(), name="job_status"),
    path("api/browse-folder/", browse_folder, name="browse_folder"),
]
