import pytest

from readorganizer_api.exceptions import NoNewChannelsAddedException
from readorganizer_api.models import Channel
from readorganizer_api.types import ChannelDataInput


def test_channel_manager_add_channels(db):
    m = Channel.objects
    channels = [
        ChannelDataInput("http://fake1/"),
        ChannelDataInput("http://fake2/"),
    ]

    m.add_channels(channels, False)

    assert m.count() == 2


def test_channel_manager_try_adding_existing_channels(db):
    m = Channel.objects
    channels = [
        ChannelDataInput("http://fake1/"),
        ChannelDataInput("http://fake2/"),
    ]

    m.add_channels(channels, False)

    with pytest.raises(NoNewChannelsAddedException):
        m.add_channels(channels, False)

    assert m.count() == 2


def test_channel_manager_add_mix_of_existing_and_new_channels(db):
    m = Channel.objects
    channels = [
        ChannelDataInput("http://fake1/"),
        ChannelDataInput("http://fake2/"),
    ]

    m.add_channels(channels, False)

    channels.append(ChannelDataInput("http://fake3"))

    m.add_channels(channels, False)

    assert m.count() == 3
