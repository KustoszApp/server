from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils.timezone import get_current_timezone
from reader import FeedExistsError
from reader import make_reader

from readorganizer_api.models import Entry
from readorganizer_api.models import EntryContent
from readorganizer_api.models import Feed
from readorganizer_api.models import SourceTypes


def get_feeds():
    feeds = []
    now = datetime.now(get_current_timezone())
    for feed in Feed.objects.filter(active=True):
        if not feed.active:
            continue

        if not feed.last_checked:
            feeds.append(feed.url)
            continue

        if (now - feed.last_checked).total_seconds() > feed.update_frequency:
            feeds.append(feed.url)

    return feeds


class Command(BaseCommand):
    help = "Fetch new articles"

    def handle(self, *args, **options):
        CACHE_DIR = Path(".") / "cache"
        READER_DB = CACHE_DIR / "readerdb.sqlite3"

        CACHE_DIR.mkdir(exist_ok=True)

        reader = make_reader(READER_DB)

        feeds_to_check = get_feeds()

        for feed_url in feeds_to_check:
            try:
                reader.add_feed(feed_url)
            except FeedExistsError:
                reader.enable_feed_updates(feed_url)

        reader.update_feeds(workers=10)

        new_entries = reader.get_entries(read=False)
        for new_entry in new_entries:
            entry_data = {
                key: getattr(new_entry, key)
                for key in ["title", "link", "updated", "published", "author"]
            }
            entry_data["feed"] = Feed.objects.get(url=new_entry.feed.url)

            django_entry = Entry(**entry_data)
            django_entry.save()

            if new_entry.summary:
                EntryContent(
                    entry=django_entry,
                    source=SourceTypes.FEED_SUMMARY,
                    content=new_entry.summary,
                ).save()
            if new_entry.content:
                content = new_entry.content[0].value
                EntryContent(
                    entry=django_entry, source=SourceTypes.FEED_CONTENT, content=content
                ).save()

            reader.mark_as_read(new_entry)

        for feed_url in feeds_to_check:
            reader.disable_feed_updates(feed_url)
