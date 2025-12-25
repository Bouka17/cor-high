import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cortexm_highlights.settings")

app = Celery("cortexm_highlights")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
