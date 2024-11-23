import json

from django.conf import settings
from django.db import migrations
from django_celery_beat.models import MINUTES

from kustosz.enums import TaskNamesEnum


def create_celery_beat(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, created = CrontabSchedule.objects.get_or_create(
        minute=0,
        hour=6,
    )

    PeriodicTask.objects.create(
        crontab=schedule,
        name="Clean expired requests_cache cache",
        task=TaskNamesEnum.CLEAN_URL_FETCHER_CACHE,
    )

class Migration(migrations.Migration):

    dependencies = [
        ("django_celery_beat", "0019_alter_periodictasks_options"),
        ("kustosz", "0004_entry_mark_as_read_20220622_1219"),
    ]

    operations = [migrations.RunPython(create_celery_beat)]
