from pathlib import Path

import yaml
from django.core.management.base import BaseCommand

from readorganizer_api.enums import ChannelTypesEnum
from readorganizer_api.exceptions import InvalidDataException
from readorganizer_api.exceptions import NoNewChannelsAddedException
from readorganizer_api.models import Channel
from readorganizer_api.tasks import add_channels
from readorganizer_api.types import AddChannelResult
from readorganizer_api.types import ChannelDataInput


class Command(BaseCommand):
    help = "Refresh configuration from settings files"

    def handle(self, *args, **options):
        CONF_DIR = Path(".") / "conf"
        FEEDS_FILE = CONF_DIR / "feeds.yaml"
        sync = True

        with open(FEEDS_FILE) as fh:
            feeds_conf = yaml.load(fh, Loader=yaml.FullLoader)

        channels = []
        for feed in feeds_conf:
            try:
                channel = ChannelDataInput(
                    url=feed.get("url"), channel_type=ChannelTypesEnum.FEED
                )
                channels.append(channel)
            except InvalidDataException as e:
                print(e.message)

        add_channels_result: AddChannelResult
        try:
            add_channels_result = add_channels(channels_list=channels)
        except NoNewChannelsAddedException:
            print("removing all channels to make debugging easier")
            Channel.objects.all().delete()
            return

        added_count = sum(item.added for item in add_channels_result.channels)
        print(f"Channels added: {added_count}")
        if sync:
            results = [t.get() for t in add_channels_result.tasks]
            print(f"Tasks return values: {results}")
