# Generated by Django 3.2.4 on 2021-09-23 19:06
from django.db import migrations

from kustosz.constants import MANUAL_CHANNEL_ID
from kustosz.enums import ChannelTypesEnum


def create_manual_channel(apps, schema_editor):
    Channel = apps.get_model("kustosz", "Channel")
    channel = Channel(
        id=MANUAL_CHANNEL_ID,
        url="file:///var/run/shm/kustosz/manual_channel",
        channel_type=ChannelTypesEnum.MANUAL,
        active=False,
    )
    channel.save()


class Migration(migrations.Migration):

    dependencies = [
        ("kustosz", "0001_initial"),
    ]

    operations = [migrations.RunPython(create_manual_channel)]