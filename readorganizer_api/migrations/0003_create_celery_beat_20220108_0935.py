# Generated by Django 3.2.4 on 2022-01-08 09:35
import json

from django.conf import settings
from django.db import migrations
from django_celery_beat.models import MINUTES

from readorganizer_api.enums import TaskNamesEnum


def create_celery_beat(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, created = IntervalSchedule.objects.get_or_create(
        every=settings.READORGANIZER_PERIODIC_FETCH_NEW_CONTENT_INTERVAL,
        period=MINUTES,
    )

    PeriodicTask.objects.create(
        interval=schedule,
        name="Fetch new channels content",
        task=TaskNamesEnum.FETCH_CHANNEL_CONTENT,
        kwargs=json.dumps({"channel_ids": None}),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("django_celery_beat", "0016_auto_20210816_2057"),
        ("readorganizer_api", "0002_create_manual_channel_20210923_1906"),
    ]

    operations = [migrations.RunPython(create_celery_beat)]
