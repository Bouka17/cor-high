from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APITestCase

from highlights.models import ProcessingJob


class APITests(APITestCase):
    def test_project_create_and_start(self):
        create_url = reverse("project-list")
        dummy = SimpleUploadedFile("match.mp4", b"fake", content_type="video/mp4")
        response = self.client.post(
            create_url,
            {"title": "Derby Night", "file": dummy},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        project_id = response.data["id"]

        start_url = reverse("project-start", args=[project_id])
        with patch("highlights.api.process_video_job.delay") as mocked_delay:
            mocked_delay.return_value.id = "task-id"
            response = self.client.post(
                start_url, {"target_duration_minutes": 5}, format="json"
            )
        self.assertEqual(response.status_code, 201)
        job_id = response.data["id"]
        job = ProcessingJob.objects.get(id=job_id)
        self.assertEqual(job.target_duration_minutes, 5)
        mocked_delay.assert_called_once()
