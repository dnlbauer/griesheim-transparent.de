import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "parliscope.settings")

app = Celery("parliscope")

# Use settings from django settings file with `CELERY_` prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover tasks in installed apps
app.autodiscover_tasks()
