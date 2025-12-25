from django.urls import path

from .consumers import JobProgressConsumer

websocket_urlpatterns = [
    path("ws/jobs/<uuid:job_id>/", JobProgressConsumer.as_asgi()),
]
