import os

from celery import Celery

from kustosz.enums import SerialQueuesNamesEnum
from kustosz.enums import TaskNamesEnum

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kustosz.settings")

app = Celery("kustosz")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.task_routes = {
    TaskNamesEnum.CLEAN_FEED_FETCHER_CACHE: {
        "queue": SerialQueuesNamesEnum.FEED_FETCHER
    },
    TaskNamesEnum.FETCH_FEED_CHANNEL_CONTENT: {
        "queue": SerialQueuesNamesEnum.FEED_FETCHER
    },
}
app.autodiscover_tasks()
