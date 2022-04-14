from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from kustosz.exceptions import InvalidDataException
from kustosz.models import Entry
from kustosz.serializers import EntryManualAddSerializer


class Command(BaseCommand):
    help = "Add entry manually"

    def add_arguments(self, parser):
        parser.add_argument("--link", required=True, help="URL of new entry")
        parser.add_argument(
            "--title", help="Title of new entry (will be read from website if omitted)"
        )
        parser.add_argument(
            "--author",
            help="Author of new entry (will be read from website if omitted)",
        )
        parser.add_argument(
            "--published_time",
            help=(
                "Published time of new entry, in ISO 8601 format "
                "(will be read from website if omitted)"
            ),
        )
        parser.add_argument(
            "--updated_time",
            help=(
                "Last updated time of new entry, in ISO 8601 format "
                "(will be read from website if omitted)"
            ),
        )
        parser.add_argument(
            "--tag",
            action="append",
            dest="tags",
            help=(
                "Tag of new entry "
                "(may be provided multiple times to specify multiple tags)"
            ),
        )

    def handle(self, *args, **options):
        keys = ("link", "title", "author", "published_time", "updated_time", "tags")
        data = {key: value for key, value in options.items() if key in keys and value}
        serializer = EntryManualAddSerializer(data=data)

        if not serializer.is_valid():
            msg = ["Invalid data provided:"]
            for flag, errors in serializer.errors.items():
                description = ", ".join([str(error) for error in errors])
                msg.append(f" --{flag}: {description}")
            raise CommandError("\n".join(msg))

        try:
            Entry.objects.add_entry_from_manual_channel(serializer.validated_data)
        except InvalidDataException as e:
            raise CommandError("\n".join(e.messages))

        self.stdout.write(self.style.SUCCESS("DONE"))
