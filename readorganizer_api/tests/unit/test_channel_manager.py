from datetime import timedelta

import pytest
from django.utils.timezone import now as django_now

import readorganizer_api
from ..framework.factories.models import ChannelFactory
from ..framework.factories.models import EntryFactory
from ..framework.factories.types import ChannelDataInputFactory
from ..framework.factories.types import FetchedFeedEntryContentFactory
from ..framework.factories.types import FetchedFeedEntryFactory
from ..framework.factories.types import FetchedFeedFactory
from readorganizer_api.enums import InternalTasksEnum
from readorganizer_api.exceptions import NoNewChannelsAddedException
from readorganizer_api.models import Channel
from readorganizer_api.types import FeedFetcherResult
from readorganizer_api.types import FetchedFeed
from readorganizer_api.utils import estimate_reading_time


def test_add_channels(db):
    m = Channel.objects
    channels = ChannelDataInputFactory.build_batch(2)

    m.add_channels(channels, False)

    assert m.count() == 2


def test_try_adding_existing_channels(db):
    m = Channel.objects
    channels = ChannelDataInputFactory.build_batch(2)

    m.add_channels(channels, False)

    with pytest.raises(NoNewChannelsAddedException):
        m.add_channels(channels, False)

    assert m.count() == 2


def test_add_mix_of_existing_and_new_channels(db):
    m = Channel.objects
    channels = ChannelDataInputFactory.build_batch(2)

    m.add_channels(channels, False)

    channels.append(ChannelDataInputFactory())

    m.add_channels(channels, False)

    assert m.count() == 3


def test_add_channel_with_tags(db):
    m = Channel.objects
    channel = ChannelDataInputFactory()

    m.add_channels([channel], False)

    assert set(channel.tags) == set(m.get().tags.names())


def test_fetch_channels_content(db, mocker):
    mocker.patch("readorganizer_api.managers.dispatch_task_by_name", return_value="1")
    ChannelFactory.create()
    m = Channel.objects
    qs = m.all()

    tasks = m.fetch_channels_content(qs, force_fetch=False)

    readorganizer_api.managers.dispatch_task_by_name.assert_called_once_with(
        InternalTasksEnum.FETCH_FEED_CHANNEL_CONTENT,
        kwargs={"channel_ids": [1], "force_fetch": False},
    )
    assert len(tasks) == 1


def test_fetch_channels_content_only_inactive(db, mocker):
    mocker.patch("readorganizer_api.managers.dispatch_task_by_name")
    ChannelFactory.create(active=False)
    m = Channel.objects
    qs = m.all()

    tasks = m.fetch_channels_content(qs, force_fetch=False)

    assert not readorganizer_api.managers.dispatch_task_by_name.called
    assert len(tasks) == 0


def test_fetch_channels_content_mix_active_inactive(db, mocker):
    mocker.patch("readorganizer_api.managers.dispatch_task_by_name", return_value="1")
    ChannelFactory.create()
    ChannelFactory.create(active=False)
    m = Channel.objects
    qs = m.all()

    tasks = m.fetch_channels_content(qs, force_fetch=False)

    readorganizer_api.managers.dispatch_task_by_name.assert_called_once_with(
        InternalTasksEnum.FETCH_FEED_CHANNEL_CONTENT,
        kwargs={"channel_ids": [1], "force_fetch": False},
    )
    assert len(tasks) == 1


def test_fetch_channels_content_paging(db, mocker):
    mocker.patch("readorganizer_api.managers.dispatch_task_by_name")
    ChannelFactory.create_batch(51)
    m = Channel.objects
    qs = m.all()

    tasks = m.fetch_channels_content(qs, force_fetch=False)

    assert readorganizer_api.managers.dispatch_task_by_name.call_count == 2
    assert len(tasks) == 2


def test_fetch_feed_channels_content(db, mocker):
    mocker.patch("readorganizer_api.managers.FeedChannelsFetcher.fetch")
    mocker.patch(
        "readorganizer_api.managers.ChannelManager._ChannelManager__update_feeds_with_fetched_data"  # noqa
    )
    mocker.patch(
        "readorganizer_api.managers.ChannelManager._ChannelManager__update_entries_with_fetched_data"  # noqa
    )
    mocker.patch("readorganizer_api.managers.dispatch_task_by_name")
    channel = ChannelFactory.create(last_check_time=django_now() - timedelta(days=365))
    m = Channel.objects

    m._fetch_feed_channels_content(channel_ids=[channel.id], force_fetch=False)

    readorganizer_api.managers.FeedChannelsFetcher.fetch.assert_called_once_with(
        feed_urls=[channel.url]
    )
    assert (
        readorganizer_api.managers.ChannelManager._ChannelManager__update_feeds_with_fetched_data.called  # noqa
    )
    assert (
        readorganizer_api.managers.ChannelManager._ChannelManager__update_entries_with_fetched_data.called  # noqa
    )


def test_fetch_feed_channels_content_updated_recently(db, mocker):
    mocker.patch("readorganizer_api.managers.FeedChannelsFetcher.fetch")
    mocker.patch(
        "readorganizer_api.managers.ChannelManager._ChannelManager__update_feeds_with_fetched_data"  # noqa
    )
    mocker.patch(
        "readorganizer_api.managers.ChannelManager._ChannelManager__update_entries_with_fetched_data"  # noqa
    )
    channel = ChannelFactory.create()
    m = Channel.objects

    m._fetch_feed_channels_content(channel_ids=[channel.id], force_fetch=False)

    assert not readorganizer_api.managers.FeedChannelsFetcher.fetch.called
    assert (
        not readorganizer_api.managers.ChannelManager._ChannelManager__update_feeds_with_fetched_data.called  # noqa
    )
    assert (
        not readorganizer_api.managers.ChannelManager._ChannelManager__update_entries_with_fetched_data.called  # noqa
    )


def test_fetch_feed_channels_content_updated_recently_force_true(db, mocker):
    mocker.patch("readorganizer_api.managers.FeedChannelsFetcher.fetch")
    mocker.patch(
        "readorganizer_api.managers.ChannelManager._ChannelManager__update_feeds_with_fetched_data"  # noqa
    )
    mocker.patch(
        "readorganizer_api.managers.ChannelManager._ChannelManager__update_entries_with_fetched_data"  # noqa
    )
    mocker.patch("readorganizer_api.managers.dispatch_task_by_name")
    channel = ChannelFactory.create()
    m = Channel.objects

    m._fetch_feed_channels_content(channel_ids=[channel.id], force_fetch=True)

    readorganizer_api.managers.FeedChannelsFetcher.fetch.assert_called_once_with(
        feed_urls=[channel.url]
    )
    assert (
        readorganizer_api.managers.ChannelManager._ChannelManager__update_feeds_with_fetched_data.called  # noqa
    )
    assert (
        readorganizer_api.managers.ChannelManager._ChannelManager__update_entries_with_fetched_data.called  # noqa
    )


def test_fetch_channels_content_channel_updated(db, mocker):
    channel = ChannelFactory.create(last_check_time=django_now() - timedelta(days=365))
    fetched_feed_data = FetchedFeedFactory(url=channel.url)
    fetcher_rv = FeedFetcherResult(feeds=[fetched_feed_data], entries=[])
    mocker.patch(
        "readorganizer_api.managers.FeedChannelsFetcher.fetch", return_value=fetcher_rv
    )
    mocker.patch(
        "readorganizer_api.managers.ChannelManager._ChannelManager__update_entries_with_fetched_data"  # noqa
    )
    m = Channel.objects

    m._fetch_feed_channels_content(channel_ids=[channel.id], force_fetch=False)

    updated_channel = m.get(pk=channel.id)
    assert updated_channel.title_upstream != channel.title_upstream
    assert updated_channel.title_upstream == fetched_feed_data.title
    assert updated_channel.link != channel.link
    assert updated_channel.link == fetched_feed_data.link
    assert updated_channel.last_check_time > channel.last_check_time
    assert (
        updated_channel.last_successful_check_time > channel.last_successful_check_time
    )


def test_fetch_channels_content_channel_not_updated_no_new_data(db, mocker):
    channel = ChannelFactory.create(last_check_time=django_now() - timedelta(days=365))
    fetched_feed_data = FetchedFeed(
        url=channel.url,
        fetch_failed=False,
        link=channel.link,
        title=channel.title_upstream,
    )
    fetcher_rv = FeedFetcherResult(feeds=[fetched_feed_data], entries=[])
    mocker.patch(
        "readorganizer_api.managers.FeedChannelsFetcher.fetch", return_value=fetcher_rv
    )
    mocker.patch(
        "readorganizer_api.managers.ChannelManager._ChannelManager__update_entries_with_fetched_data"  # noqa
    )
    m = Channel.objects

    m._fetch_feed_channels_content(channel_ids=[channel.id], force_fetch=False)

    updated_channel = m.get(pk=channel.id)
    assert updated_channel.title_upstream == channel.title_upstream
    assert updated_channel.title_upstream == fetched_feed_data.title
    assert updated_channel.link == channel.link
    assert updated_channel.link == fetched_feed_data.link
    assert updated_channel.last_check_time > channel.last_check_time
    assert (
        updated_channel.last_successful_check_time > channel.last_successful_check_time
    )


def test_fetch_channels_content_channel_not_updated_fetch_failure(db, mocker):
    channel = ChannelFactory.create(last_check_time=django_now() - timedelta(days=365))
    fetched_feed_data = FetchedFeed(
        url=channel.url,
        fetch_failed=True,
    )
    fetcher_rv = FeedFetcherResult(feeds=[fetched_feed_data], entries=[])
    mocker.patch(
        "readorganizer_api.managers.FeedChannelsFetcher.fetch", return_value=fetcher_rv
    )
    mocker.patch(
        "readorganizer_api.managers.ChannelManager._ChannelManager__update_entries_with_fetched_data"  # noqa
    )
    m = Channel.objects

    m._fetch_feed_channels_content(channel_ids=[channel.id], force_fetch=False)

    updated_channel = m.get(pk=channel.id)
    assert updated_channel.title_upstream == channel.title_upstream
    assert updated_channel.title_upstream != fetched_feed_data.title
    assert updated_channel.link == channel.link
    assert updated_channel.link != fetched_feed_data.link
    assert updated_channel.last_check_time > channel.last_check_time
    assert (
        updated_channel.last_successful_check_time == channel.last_successful_check_time
    )
    assert updated_channel.last_check_time > updated_channel.last_successful_check_time


def test_fetch_channels_content_channel_mix_updated_fetch_failure(db, mocker):
    channel1 = ChannelFactory.create(last_check_time=django_now() - timedelta(days=365))
    channel2 = ChannelFactory.create(last_check_time=django_now() - timedelta(days=365))
    fetched_feed_data1 = FetchedFeedFactory(url=channel1.url)
    fetched_feed_data2 = FetchedFeed(
        url=channel2.url,
        fetch_failed=True,
    )
    fetcher_rv = FeedFetcherResult(
        feeds=[fetched_feed_data1, fetched_feed_data2], entries=[]
    )
    mocker.patch(
        "readorganizer_api.managers.FeedChannelsFetcher.fetch", return_value=fetcher_rv
    )
    mocker.patch(
        "readorganizer_api.managers.ChannelManager._ChannelManager__update_entries_with_fetched_data"  # noqa
    )
    m = Channel.objects

    m._fetch_feed_channels_content(
        channel_ids=[channel1.id, channel2.id], force_fetch=False
    )

    updated_channel1 = m.get(pk=channel1.id)
    updated_channel2 = m.get(pk=channel2.id)
    assert updated_channel1.title_upstream != channel1.title_upstream
    assert updated_channel1.title_upstream == fetched_feed_data1.title
    assert updated_channel1.link != channel1.link
    assert updated_channel1.link == fetched_feed_data1.link
    assert updated_channel1.last_check_time > channel1.last_check_time
    assert (
        updated_channel1.last_successful_check_time
        > channel1.last_successful_check_time
    )
    assert updated_channel2.title_upstream == channel2.title_upstream
    assert updated_channel2.title_upstream != fetched_feed_data2.title
    assert updated_channel2.link == channel2.link
    assert updated_channel2.link != fetched_feed_data2.link
    assert updated_channel2.last_check_time > channel2.last_check_time
    assert (
        updated_channel2.last_successful_check_time
        == channel2.last_successful_check_time
    )
    assert (
        updated_channel2.last_check_time > updated_channel2.last_successful_check_time
    )


def test_fetch_feed_channels_entry_added(db, mocker):
    channel = ChannelFactory.create(last_check_time=django_now() - timedelta(days=365))
    fetched_entry_data = FetchedFeedEntryFactory(feed_url=channel.url)
    fetcher_rv = FeedFetcherResult(feeds=[], entries=[fetched_entry_data])
    mocker.patch(
        "readorganizer_api.managers.FeedChannelsFetcher.fetch", return_value=fetcher_rv
    )
    mocker.patch(
        "readorganizer_api.managers.ChannelManager._ChannelManager__update_feeds_with_fetched_data"  # noqa
    )
    mocker.patch("readorganizer_api.managers.dispatch_task_by_name")
    m = Channel.objects

    m._fetch_feed_channels_content(channel_ids=[channel.id], force_fetch=False)

    new_entry = channel.entries.get()
    assert new_entry.gid == fetched_entry_data.gid
    assert new_entry.link == fetched_entry_data.link
    assert new_entry.title == fetched_entry_data.title
    assert new_entry.author == fetched_entry_data.author
    assert new_entry.published_time_upstream == fetched_entry_data.published_time
    assert new_entry.updated_time_upstream == fetched_entry_data.updated_time
    assert new_entry.added_time > fetched_entry_data.published_time
    new_entry_content = new_entry.content_set.get()
    assert new_entry_content.source == fetched_entry_data.content[0].source
    assert new_entry_content.content == fetched_entry_data.content[0].content
    assert new_entry_content.language == fetched_entry_data.content[0].language
    assert new_entry_content.mimetype == fetched_entry_data.content[0].mimetype


def test_fetch_feed_channels_entry_updated(db, mocker):
    channel = ChannelFactory.create(last_check_time=django_now() - timedelta(days=365))
    entry = EntryFactory.create(channel=channel)
    fetched_entry_data = FetchedFeedEntryFactory(feed_url=channel.url, gid=entry.gid)
    fetcher_rv = FeedFetcherResult(feeds=[], entries=[fetched_entry_data])
    mocker.patch(
        "readorganizer_api.managers.FeedChannelsFetcher.fetch", return_value=fetcher_rv
    )
    mocker.patch(
        "readorganizer_api.managers.ChannelManager._ChannelManager__update_feeds_with_fetched_data"  # noqa
    )
    mocker.patch("readorganizer_api.managers.dispatch_task_by_name")
    m = Channel.objects

    m._fetch_feed_channels_content(channel_ids=[channel.id], force_fetch=False)

    updated_entry = channel.entries.get(pk=entry.pk)
    assert updated_entry.link != entry.link
    assert updated_entry.link == fetched_entry_data.link
    assert updated_entry.title != entry.title
    assert updated_entry.title == fetched_entry_data.title
    assert updated_entry.author != entry.author
    assert updated_entry.author == fetched_entry_data.author
    assert updated_entry.published_time_upstream != entry.published_time_upstream
    assert updated_entry.published_time_upstream == fetched_entry_data.published_time
    assert updated_entry.updated_time_upstream != entry.updated_time_upstream
    assert updated_entry.updated_time_upstream == fetched_entry_data.updated_time
    assert updated_entry.updated_time > entry.added_time


def test_fetch_feed_channels_entry_not_updated_no_new_data(db, mocker):
    channel = ChannelFactory.create(last_check_time=django_now() - timedelta(days=365))
    entry = EntryFactory.create(channel=channel)
    fetched_entry_data = FetchedFeedEntryFactory(
        feed_url=channel.url,
        gid=entry.gid,
        link=entry.link,
        title=entry.title,
        author=entry.author,
        published_time=entry.published_time_upstream,
        updated_time=entry.updated_time_upstream,
        content=[],
    )
    fetcher_rv = FeedFetcherResult(feeds=[], entries=[fetched_entry_data])
    mocker.patch(
        "readorganizer_api.managers.FeedChannelsFetcher.fetch", return_value=fetcher_rv
    )
    mocker.patch(
        "readorganizer_api.managers.ChannelManager._ChannelManager__update_feeds_with_fetched_data"  # noqa
    )
    mocker.patch("readorganizer_api.managers.dispatch_task_by_name")
    m = Channel.objects

    m._fetch_feed_channels_content(channel_ids=[channel.id], force_fetch=False)

    updated_entry = channel.entries.get(pk=entry.pk)
    assert updated_entry.link == entry.link
    assert updated_entry.link == fetched_entry_data.link
    assert updated_entry.title == entry.title
    assert updated_entry.title == fetched_entry_data.title
    assert updated_entry.author == entry.author
    assert updated_entry.author == fetched_entry_data.author
    assert updated_entry.published_time_upstream == entry.published_time_upstream
    assert updated_entry.published_time_upstream == fetched_entry_data.published_time
    assert updated_entry.updated_time_upstream == entry.updated_time_upstream
    assert updated_entry.updated_time_upstream == fetched_entry_data.updated_time
    assert updated_entry.updated_time == entry.updated_time


def test_fetch_feed_channels_entry_content_updated(db, mocker):
    channel = ChannelFactory.create(last_check_time=django_now() - timedelta(days=365))
    entry = EntryFactory.create(channel=channel, content_set=1)
    entry_content = entry.content_set.first()
    fetched_entry_content = FetchedFeedEntryContentFactory(
        source=entry_content.source,
        mimetype=entry_content.mimetype,
        language=entry_content.language,
    )
    fetched_entry_data = FetchedFeedEntryFactory(
        feed_url=channel.url, gid=entry.gid, content=[fetched_entry_content]
    )
    fetcher_rv = FeedFetcherResult(feeds=[], entries=[fetched_entry_data])
    mocker.patch(
        "readorganizer_api.managers.FeedChannelsFetcher.fetch", return_value=fetcher_rv
    )
    mocker.patch(
        "readorganizer_api.managers.ChannelManager._ChannelManager__update_feeds_with_fetched_data"  # noqa
    )
    mocker.patch("readorganizer_api.managers.dispatch_task_by_name")
    m = Channel.objects

    m._fetch_feed_channels_content(channel_ids=[channel.id], force_fetch=False)

    updated_entry = channel.entries.get(pk=entry.pk)
    assert updated_entry.content_set.count() == 1
    updated_entry_content = updated_entry.content_set.first()
    assert updated_entry_content.source == entry_content.source
    assert updated_entry_content.source == fetched_entry_content.source
    assert updated_entry_content.mimetype == entry_content.mimetype
    assert updated_entry_content.mimetype == fetched_entry_content.mimetype
    assert updated_entry_content.language == entry_content.language
    assert updated_entry_content.language == fetched_entry_content.language
    assert updated_entry_content.content != entry_content.content
    assert updated_entry_content.content == fetched_entry_content.content
    assert updated_entry_content.estimated_reading_time == estimate_reading_time(
        fetched_entry_content.content
    )


def test_fetch_feed_channels_entry_content_added(db, mocker):
    channel = ChannelFactory.create(last_check_time=django_now() - timedelta(days=365))
    entry = EntryFactory.create(channel=channel, content_set=1)
    entry_content = entry.content_set.first()
    fetched_entry_content = FetchedFeedEntryContentFactory()
    fetched_entry_data = FetchedFeedEntryFactory(
        feed_url=channel.url, gid=entry.gid, content=[fetched_entry_content]
    )
    fetcher_rv = FeedFetcherResult(feeds=[], entries=[fetched_entry_data])
    mocker.patch(
        "readorganizer_api.managers.FeedChannelsFetcher.fetch", return_value=fetcher_rv
    )
    mocker.patch(
        "readorganizer_api.managers.ChannelManager._ChannelManager__update_feeds_with_fetched_data"  # noqa
    )
    mocker.patch("readorganizer_api.managers.dispatch_task_by_name")
    m = Channel.objects

    m._fetch_feed_channels_content(channel_ids=[channel.id], force_fetch=False)

    updated_entry = channel.entries.get(pk=entry.pk)
    assert updated_entry.content_set.count() == 2
    new_entry_content = updated_entry.content_set.last()
    assert new_entry_content.source == fetched_entry_content.source
    assert new_entry_content.mimetype == fetched_entry_content.mimetype
    assert new_entry_content.language == fetched_entry_content.language
    assert new_entry_content.content != entry_content.content
    assert new_entry_content.content == fetched_entry_content.content
    assert new_entry_content.estimated_reading_time == estimate_reading_time(
        fetched_entry_content.content
    )
    assert (
        updated_entry.content_set.first().estimated_reading_time
        == entry_content.estimated_reading_time
    )


def test_fetch_feed_channels_entry_content_not_updated_no_changes(db, mocker):
    channel = ChannelFactory.create(last_check_time=django_now() - timedelta(days=365))
    entry = EntryFactory.create(channel=channel, content_set=1)
    entry_content = entry.content_set.first()
    fetched_entry_content = FetchedFeedEntryContentFactory(
        content=entry_content.content,
        source=entry_content.source,
        mimetype=entry_content.mimetype,
        language=entry_content.language,
    )
    fetched_entry_data = FetchedFeedEntryFactory(
        feed_url=channel.url, gid=entry.gid, content=[fetched_entry_content]
    )
    fetcher_rv = FeedFetcherResult(feeds=[], entries=[fetched_entry_data])
    mocker.patch(
        "readorganizer_api.managers.FeedChannelsFetcher.fetch", return_value=fetcher_rv
    )
    mocker.patch(
        "readorganizer_api.managers.ChannelManager._ChannelManager__update_feeds_with_fetched_data"  # noqa
    )
    mocker.patch("readorganizer_api.managers.dispatch_task_by_name")
    m = Channel.objects

    m._fetch_feed_channels_content(channel_ids=[channel.id], force_fetch=False)

    updated_entry = channel.entries.get(pk=entry.pk)
    assert updated_entry.content_set.count() == 1
    updated_entry_content = updated_entry.content_set.first()
    assert updated_entry_content.source == entry_content.source
    assert updated_entry_content.source == fetched_entry_content.source
    assert updated_entry_content.mimetype == entry_content.mimetype
    assert updated_entry_content.mimetype == fetched_entry_content.mimetype
    assert updated_entry_content.language == entry_content.language
    assert updated_entry_content.language == fetched_entry_content.language
    assert updated_entry_content.content == entry_content.content
    assert updated_entry_content.content == fetched_entry_content.content
    assert (
        updated_entry_content.estimated_reading_time
        == entry_content.estimated_reading_time
    )
