import pytest

from .framework.factories.types import ChannelDataInputFactory
from readorganizer_api.exceptions import NoNewChannelsAddedException
from readorganizer_api.models import Channel


def test_channel_manager_add_channels(db):
    m = Channel.objects
    channels = ChannelDataInputFactory.build_batch(2)

    m.add_channels(channels, False)

    assert m.count() == 2


def test_channel_manager_try_adding_existing_channels(db):
    m = Channel.objects
    channels = ChannelDataInputFactory.build_batch(2)

    m.add_channels(channels, False)

    with pytest.raises(NoNewChannelsAddedException):
        m.add_channels(channels, False)

    assert m.count() == 2


def test_channel_manager_add_mix_of_existing_and_new_channels(db):
    m = Channel.objects
    channels = ChannelDataInputFactory.build_batch(2)

    m.add_channels(channels, False)

    channels.append(ChannelDataInputFactory())

    m.add_channels(channels, False)

    assert m.count() == 3


def test_channel_manager_add_channel_with_tags(db):
    m = Channel.objects
    channel = ChannelDataInputFactory()

    m.add_channels([channel], False)

    assert set(channel.tags) == set(m.get().tags.names())
