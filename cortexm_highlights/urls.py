from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from highlights.api import EventLogViewSet, ProcessingJobViewSet, ProjectViewSet, SegmentViewSet

router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="project")
router.register("jobs", ProcessingJobViewSet, basename="job")
router.register("segments", SegmentViewSet, basename="segment")
router.register("events", EventLogViewSet, basename="event")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("", include("highlights.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
