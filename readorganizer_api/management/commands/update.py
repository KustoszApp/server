from django.core.management.base import BaseCommand

from readorganizer_api.models import Channel


class Command(BaseCommand):
    help = "Fetch new articles"

    def handle(self, *args, **options):
        channels = Channel.objects.filter(active=True)
        # FIXME: debugging only
        channels.first().entries.first().delete()
        # FIXME: end debugging only
        Channel.objects.fetch_channels_content(channels, True)
