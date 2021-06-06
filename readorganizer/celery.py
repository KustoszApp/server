import os

from celery import Celery

from readorganizer_api.enums import InternalTasksEnum

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "readorganizer.settings")

app = Celery("readorganizer")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.task_routes = {
    InternalTasksEnum.FETCH_FEED_CHANNEL_CONTENT: {"queue": "fetch_channels_content"}
}
app.autodiscover_tasks()
