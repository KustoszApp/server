from pathlib import Path

import yaml
from django.core.management.base import BaseCommand

from readorganizer_api.models import Feed


class Command(BaseCommand):
    help = "Refresh configuration from settings files"

    def handle(self, *args, **options):
        CONF_DIR = Path(".") / "conf"
        FEEDS_FILE = CONF_DIR / "feeds.yaml"

        with open(FEEDS_FILE) as fh:
            feeds_conf = yaml.load(fh, Loader=yaml.FullLoader)

        for feed in feeds_conf:
            try:
                f = Feed.objects.get(url=feed.get("url"))
                for key, value in feed.items():
                    setattr(f, key, value)
            except Feed.DoesNotExist:
                f = Feed(**feed)
            f.save()
