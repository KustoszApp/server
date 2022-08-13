from pathlib import Path

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from kustosz.models import Channel


class Command(BaseCommand):
    help = "Export channels into OPML file"

    def add_arguments(self, parser):
        parser.add_argument("--file", help="Path to file")
        parser.add_argument(
            "--force", action="store_true", help="Overwrite existing file"
        )

    def handle(self, *args, **options):
        file_arg = Path(options.get("file"))
        force_arg = options.get("force")
        if file_arg.exists() and not force_arg:
            msg = f"{file_arg.as_posix()} already exists. Use --force to overwrite it."
            raise CommandError(msg)

        self.stdout.write(f"Exporting channels to {file_arg.as_posix()}...")
        opml_content = Channel.objects.export_channels_opml()
        with open(file_arg, "w") as fh:
            fh.write(opml_content)
        self.stdout.write(self.style.SUCCESS("DONE"))
