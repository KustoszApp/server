from pathlib import Path

import yaml
from django.core.management.base import BaseCommand

from readorganizer_api.enums import ChannelTypesEnum
from readorganizer_api.exceptions import NoNewChannelsAddedException
from readorganizer_api.models import Channel
from readorganizer_api.tasks import add_channels
from readorganizer_api.types import ChannelDataInput


class Command(BaseCommand):
    help = "Refresh configuration from settings files"

    def handle(self, *args, **options):
        CONF_DIR = Path(".") / "conf"
        FEEDS_FILE = CONF_DIR / "feeds.yaml"
        sync = True

        with open(FEEDS_FILE) as fh:
            feeds_conf = yaml.load(fh, Loader=yaml.FullLoader)

        channels = [
            ChannelDataInput(uri=feed.get("url"), channel_type=ChannelTypesEnum.FEED)
            for feed in feeds_conf
        ]

        try:
            added_id, tasks = add_channels(channels_list=channels)
        except NoNewChannelsAddedException:
            print("removing all channels to make debugging easier")
            Channel.objects.all().delete()
            return

        print(f"Channels added: {len(added_id)}")
        if sync:
            results = [t.get() for t in tasks]
            print(f"Tasks return values: {results}")
