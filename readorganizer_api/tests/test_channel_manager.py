from datetime import timedelta

import pytest
from django.utils.timezone import now as django_now

import readorganizer_api
from .framework.factories.models import ChannelFactory
from .framework.factories.types import ChannelDataInputFactory
from readorganizer_api.enums import InternalTasksEnum
from readorganizer_api.exceptions import NoNewChannelsAddedException
from readorganizer_api.models import Channel


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
