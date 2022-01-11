from datetime import timedelta

from django.urls import reverse
from django.utils.timezone import now as django_now
from rest_framework import status
from rest_framework.fields import DateTimeField

from ..framework.factories.models import ChannelFactory
from ..framework.factories.models import EntryFactory
from readorganizer.enums import ChannelTypesEnum
from readorganizer.models import Channel


def test_deactivate_id(db, authenticated_api_client):
    channels = ChannelFactory.create_batch(5)
    channels_to_update = channels[1:3]
    updated_channels_id = [ch.pk for ch in channels_to_update]
    url = (
        reverse("channels_inactivate")
        + f"?id={','.join(str(_) for _ in updated_channels_id)}"
    )

    response = authenticated_api_client.post(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["inactivated_count"] == len(channels_to_update)
    assert response.data["inactivated_channels"] == updated_channels_id
    channel_objects = Channel.objects.exclude(channel_type=ChannelTypesEnum.MANUAL)
    assert channel_objects.filter(active=False).count() == len(channels_to_update)
    assert channel_objects.filter(active=True).count() == (5 - len(channels_to_update))
    for channel in channels_to_update:
        channel.refresh_from_db()
        assert channel.active is False


def test_deactivate_stale(db, authenticated_api_client):
    fresh_channel = ChannelFactory()
    stale_channel = ChannelFactory(
        last_successful_check_time=django_now() - timedelta(days=100)
    )
    url = reverse("channels_inactivate") + "?is_stale=1"

    response = authenticated_api_client.post(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["inactivated_count"] == 1
    assert response.data["inactivated_channels"] == [stale_channel.pk]
    channel_objects = Channel.objects.exclude(channel_type=ChannelTypesEnum.MANUAL)
    assert channel_objects.filter(active=False).count() == 1
    assert channel_objects.filter(active=True).count() == 1
    stale_channel.refresh_from_db()
    assert stale_channel.active is False
    fresh_channel.refresh_from_db()
    fresh_channel.active is True


def test_deactivate_no_new_entries(db, authenticated_api_client):
    new_channel = ChannelFactory()
    old_channel = ChannelFactory()
    EntryFactory(channel=new_channel)
    EntryFactory(
        channel=old_channel,
        published_time_upstream=None,
        updated_time_upstream=django_now() - timedelta(days=100),
    )
    reference_date = django_now() - timedelta(days=99)
    reference_date_str = DateTimeField().to_representation(reference_date)
    url = (
        reverse("channels_inactivate")
        + f"?last_entry_published_time__lte={reference_date_str}"
    )

    response = authenticated_api_client.post(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["inactivated_count"] == 1
    assert response.data["inactivated_channels"] == [old_channel.pk]
    channel_objects = Channel.objects.exclude(channel_type=ChannelTypesEnum.MANUAL)
    assert channel_objects.filter(active=False).count() == 1
    assert channel_objects.filter(active=True).count() == 1
    old_channel.refresh_from_db()
    assert old_channel.active is False
    new_channel.refresh_from_db()
    assert new_channel.active is True


def test_activate_id(db, authenticated_api_client):
    channels = ChannelFactory.create_batch(5, active=False)
    channels_to_update = channels[1:3]
    updated_channels_id = [ch.pk for ch in channels_to_update]
    url = (
        reverse("channels_activate")
        + f"?id={','.join(str(_) for _ in updated_channels_id)}"
    )

    response = authenticated_api_client.post(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["activated_count"] == len(channels_to_update)
    assert response.data["activated_channels"] == updated_channels_id
    channel_objects = Channel.objects.exclude(channel_type=ChannelTypesEnum.MANUAL)
    assert channel_objects.filter(active=True).count() == len(channels_to_update)
    assert channel_objects.filter(active=False).count() == (5 - len(channels_to_update))
    for channel in channels_to_update:
        channel.refresh_from_db()
        assert channel.active is True


def test_activate_all(db, authenticated_api_client):
    channels = ChannelFactory.create_batch(5, active=False)
    url = reverse("channels_activate") + "?active=False"

    response = authenticated_api_client.post(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["activated_count"] == len(channels)
    assert response.data["activated_channels"] == [ch.pk for ch in channels]
    channel_objects = Channel.objects.exclude(channel_type=ChannelTypesEnum.MANUAL)
    assert channel_objects.filter(active=True).count() == len(channels)
    assert channel_objects.filter(active=False).count() == 0
    for channel in channels:
        channel.refresh_from_db()
        assert channel.active is True
