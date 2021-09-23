from pathlib import Path

from django.conf import settings

DEFAULT_UPDATE_FREQUENCY = 3600
MANUAL_CHANNEL_ID = 1
FETCHERS_CACHE_DIR: Path = settings.BASE_DIR / "cache"
FEED_FETCHER_LOCAL_FEEDS_DIR: Path = settings.BASE_DIR / "feeds"
