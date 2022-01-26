from pathlib import Path

import listparser
import yaml
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from kustosz.constants import FEED_FETCHER_LOCAL_FEEDS_DIR
from kustosz.enums import ChannelTypesEnum
from kustosz.enums import ImportChannelsActionsEnum
from kustosz.exceptions import InvalidDataException
from kustosz.exceptions import NoNewChannelsAddedException
from kustosz.tasks import add_channels
from kustosz.types import AddChannelResult
from kustosz.types import ChannelDataInput


class Command(BaseCommand):
    help = "Import new channels from file or local directory"

    def add_arguments(self, parser):
        valid_actions = ", ".join(ImportChannelsActionsEnum.values)
        parser.add_argument(
            "--wait", action="store_true", help="Wait for background jobs to finish"
        )
        parser.add_argument(
            "--no-fetch",
            action="store_true",
            help=(
                "Don't fetch content from newly added channels; "
                "this is probably only useful during debugging"
            ),
        )
        parser.add_argument("--file", help="Path to file that should be imported")
        parser.add_argument("action", nargs=1, help=f"One of {valid_actions}")

    def get_channels_autodiscover(self, path):
        channels = []
        for foundfile in FEED_FETCHER_LOCAL_FEEDS_DIR.glob("**/*"):
            if foundfile.is_dir():
                continue
            relative_path = foundfile.relative_to(FEED_FETCHER_LOCAL_FEEDS_DIR)
            url = f"file://{relative_path}"
            try:
                channel = ChannelDataInput(url=url, channel_type=ChannelTypesEnum.FEED)
                channels.append(channel)
            except InvalidDataException as e:
                self.stderr.write(e.message)
        return channels

    def get_channels_opml(self, path):
        lp = listparser.parse(str(path))
        if lp.get("bozo"):
            msg = (
                f'Failed to process "{path}"; listparser reported:\n',
                lp.get("bozo_exception"),
            )
            raise CommandError(msg)

        channels = []
        for feed in lp.get("feeds"):
            try:
                channel = ChannelDataInput(
                    url=feed.get("url"),
                    channel_type=ChannelTypesEnum.FEED,
                    title=feed.get("title"),
                    tags=feed.get("tags"),
                )
                channels.append(channel)
            except InvalidDataException as e:
                self.stderr.write(e.message)
            except TypeError as e:
                self.stderr.write(e)
        return channels

    def get_channels_config(self, path):
        with open(path) as fh:
            feeds_conf = yaml.load(fh, Loader=yaml.FullLoader)

        channels = []
        for feed in feeds_conf:
            try:
                channel = ChannelDataInput(**feed, channel_type=ChannelTypesEnum.FEED)
                channels.append(channel)
            except InvalidDataException as e:
                self.stderr.write(e.message)
            except TypeError as e:
                self.stderr.write(e)
        return channels

    def handle(self, *args, **options):
        fetch_content = not options.get("no_fetch")
        action = next(iter(options.get("action")))
        if action not in ImportChannelsActionsEnum:
            valid_actions = ", ".join(ImportChannelsActionsEnum.values)
            msg = f'Invalid action: "{action}"; action must be one of: {valid_actions}'
            raise CommandError(msg)

        actions_requiring_file = (
            ImportChannelsActionsEnum.OPML,
            ImportChannelsActionsEnum.CONFIG,
        )

        file_arg = options.get("file")

        if action in actions_requiring_file:
            if not file_arg:
                msg = f"{action} requires --file command line argument"
                raise CommandError(msg)
            file_arg = Path(file_arg)
            if not file_arg.exists():
                msg = f"{file_arg} doesn't exist"
                raise CommandError(msg)

        action_handler = getattr(self, f"get_channels_{action}")

        channels = action_handler(file_arg)

        self.stdout.write(f"Found {len(channels)} channels...")

        add_channels_result: AddChannelResult
        try:
            add_channels_result = add_channels(
                channels_list=channels, fetch_content=fetch_content
            )
            added_count = sum(item.added for item in add_channels_result.channels)
        except NoNewChannelsAddedException:
            added_count = 0

        self.stdout.write(f"Added {added_count} new channels...")
        if added_count and options.get("wait"):
            bg_jobs_count = len(add_channels_result.tasks)
            self.stdout.write(
                f"Waiting for {bg_jobs_count} background job(s) to finish..."
            )
            for task in add_channels_result.tasks:
                task.get()
        self.stdout.write(self.style.SUCCESS("DONE"))
