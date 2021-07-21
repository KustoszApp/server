from datetime import timedelta

from django.urls import reverse
from django.utils.timezone import now as django_now
from rest_framework import status
from rest_framework.fields import DateTimeField
from rest_framework.test import APIClient

from ..framework.factories.models import ChannelFactory
from ..framework.factories.models import EntryFactory
from readorganizer_api.models import Channel


def test_deactivate_id(db):
    channels = ChannelFactory.create_batch(5)
    channels_to_update = channels[1:3]
    updated_channels_id = [ch.pk for ch in channels_to_update]
    client = APIClient()
    url = (
        reverse("channels_inactivate")
        + f"?id={','.join(str(_) for _ in updated_channels_id)}"
    )

    response = client.post(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["inactivated_count"] == len(channels_to_update)
    assert response.data["inactivated_channels"] == updated_channels_id
    assert Channel.objects.filter(active=False).count() == len(channels_to_update)
    assert Channel.objects.filter(active=True).count() == (5 - len(channels_to_update))
    for channel in channels_to_update:
        channel.refresh_from_db()
        assert channel.active is False


def test_deactivate_stale(db):
    fresh_channel = ChannelFactory()
    stale_channel = ChannelFactory(
        last_successful_check_time=django_now() - timedelta(days=100)
    )
    client = APIClient()
    url = reverse("channels_inactivate") + "?is_stale=1"

    response = client.post(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["inactivated_count"] == 1
    assert response.data["inactivated_channels"] == [stale_channel.pk]
    assert Channel.objects.filter(active=False).count() == 1
    assert Channel.objects.filter(active=True).count() == 1
    stale_channel.refresh_from_db()
    assert stale_channel.active is False
    fresh_channel.refresh_from_db()
    fresh_channel.active is True


def test_deactivate_no_new_entries(db):
    new_channel = ChannelFactory()
    old_channel = ChannelFactory()
    EntryFactory(channel=new_channel)
    EntryFactory(
        channel=old_channel,
        published_time_upstream=None,
        updated_time_upstream=django_now() - timedelta(days=100),
    )
    client = APIClient()
    reference_date = django_now() - timedelta(days=99)
    reference_date_str = DateTimeField().to_representation(reference_date)
    url = (
        reverse("channels_inactivate")
        + f"?last_entry_published_time__lte={reference_date_str}"
    )

    response = client.post(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["inactivated_count"] == 1
    assert response.data["inactivated_channels"] == [old_channel.pk]
    assert Channel.objects.filter(active=False).count() == 1
    assert Channel.objects.filter(active=True).count() == 1
    old_channel.refresh_from_db()
    assert old_channel.active is False
    new_channel.refresh_from_db()
    assert new_channel.active is True
