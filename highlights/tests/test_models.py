from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from highlights.models import ProcessingJob, Project, VideoAsset


class ModelTests(TestCase):
    def test_project_and_job_defaults(self):
        project = Project.objects.create(title="Matchday 12")
        job = ProcessingJob.objects.create(project=project, target_duration_minutes=5)
        self.assertEqual(job.status, ProcessingJob.Status.PENDING)
        self.assertEqual(job.progress, 0)

    def test_video_asset_creation(self):
        project = Project.objects.create(title="Matchday 13")
        dummy = SimpleUploadedFile("match.mp4", b"fake", content_type="video/mp4")
        asset = VideoAsset.objects.create(
            project=project, file=dummy, original_filename="match.mp4"
        )
        self.assertEqual(asset.project, project)
        self.assertEqual(asset.original_filename, "match.mp4")
