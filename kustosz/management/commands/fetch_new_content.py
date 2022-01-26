from django.core.management.base import BaseCommand

from kustosz.models import Channel


class Command(BaseCommand):
    help = "Fetch new articles from active channels"

    def add_arguments(self, parser):
        parser.add_argument(
            "--wait", action="store_true", help="Wait for background jobs to finish"
        )
        parser.add_argument(
            "--force-fetch",
            action="store_true",
            help=(
                "Fetch content from channels that were already checked "
                "less than update_frequency seconds ago"
            ),
        )
        parser.add_argument("channel_ids", nargs="*", help="ids of channels to fetch")

    def handle(self, *args, **options):
        channels = Channel.objects.filter(active=True)
        requested_channel_ids = options.get("channel_ids")
        if requested_channel_ids:
            channels = channels.filter(pk__in=requested_channel_ids)

        if not channels:
            self.stdout.write("No active channels considered for update, exiting")
            return

        force_fetch = options.get("force_fetch")

        tasks = Channel.objects.fetch_channels_content(channels, force_fetch)

        if options.get("wait"):
            bg_jobs_count = len(tasks)
            self.stdout.write(
                f"Waiting for {bg_jobs_count} background job(s) to finish..."
            )
            for task in tasks:
                task.get()
        self.stdout.write(self.style.SUCCESS("DONE"))
