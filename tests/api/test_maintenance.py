from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils.timezone import now as django_now
from rest_framework import status
from rest_framework.fields import DateTimeField

from ..framework.factories.models import ChannelFactory
from ..framework.factories.models import EntryFactory
from kustosz.enums import ChannelTypesEnum
from kustosz.models import Channel
from kustosz.models import Entry


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


def test_delete_id(db, mocker, authenticated_api_client):
    mocker.patch("kustosz.managers.dispatch_task_by_name")
    channels = ChannelFactory.create_batch(5, active=False)
    channels_to_delete = channels[1:3]
    deleted_channels_id = [ch.pk for ch in channels_to_delete]
    url = (
        reverse("channels_delete")
        + f"?id={','.join(str(_) for _ in deleted_channels_id)}"
    )

    response = authenticated_api_client.post(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["deleted_count"] == len(deleted_channels_id)
    assert response.data["deleted_channels"] == deleted_channels_id
    channel_objects = Channel.objects.exclude(channel_type=ChannelTypesEnum.MANUAL)
    assert channel_objects.count() == (5 - len(deleted_channels_id))
    for channel in channels_to_delete:
        with pytest.raises(Channel.DoesNotExist):
            channel.refresh_from_db()


def test_delete_all(db, mocker, authenticated_api_client):
    mocker.patch("kustosz.managers.dispatch_task_by_name")
    channels = ChannelFactory.create_batch(5, active=False, entries=3)
    url = reverse("channels_delete") + "?active=False"

    response = authenticated_api_client.post(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["deleted_count"] == len(channels)
    assert response.data["deleted_channels"] == [ch.pk for ch in channels]
    channel_objects = Channel.objects.exclude(channel_type=ChannelTypesEnum.MANUAL)
    assert channel_objects.count() == 0
    for channel in channels:
        with pytest.raises(Channel.DoesNotExist):
            channel.refresh_from_db()


def test_delete_keep_tagged(db, faker, mocker, authenticated_api_client):
    mocker.patch("kustosz.managers.dispatch_task_by_name")
    all_tags = [w.title() for w in faker.words(nb=5, unique=True)]
    channels = ChannelFactory.create_batch(5, active=False, entries=3)
    tagged_entries = []
    deleted_entries = []
    for idx, channel in enumerate(channels):
        for entry in channel.entries.all():
            entry_tags = faker.random.sample(all_tags, k=faker.pyint(max_value=5))
            if idx % 2 or not entry_tags:
                deleted_entries.append(entry)
                continue
            entry.tags.add(*entry_tags)
            tagged_entries.append(entry)
    url = reverse("channels_delete") + "?active=False"
    data = {"keep_tagged_entries": True}

    response = authenticated_api_client.post(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["deleted_count"] == len(channels)
    assert response.data["deleted_channels"] == [ch.pk for ch in channels]
    channel_objects = Channel.objects.exclude(channel_type=ChannelTypesEnum.MANUAL)
    assert channel_objects.count() == 0
    manual_channel = Channel.objects.get(channel_type=ChannelTypesEnum.MANUAL)
    assert manual_channel.entries.count() == len(tagged_entries)
    for entry in tagged_entries:
        entry.refresh_from_db()
        assert entry.channel == manual_channel
    for entry in deleted_entries:
        with pytest.raises(Entry.DoesNotExist):
            entry.refresh_from_db()


def test_delete_dont_keep_tagged(db, faker, mocker, authenticated_api_client):
    mocker.patch("kustosz.managers.dispatch_task_by_name")
    all_tags = [w.title() for w in faker.words(nb=5, unique=True)]
    channels = ChannelFactory.create_batch(5, active=False, entries=3)
    tagged_entries = []
    deleted_entries = []
    for idx, channel in enumerate(channels):
        for entry in channel.entries.all():
            entry_tags = faker.random.sample(all_tags, k=faker.pyint(max_value=5))
            if idx % 2 or not entry_tags:
                deleted_entries.append(entry)
                continue
            entry.tags.add(*entry_tags)
            tagged_entries.append(entry)
    url = reverse("channels_delete") + "?active=False"
    data = {"keep_tagged_entries": False}

    response = authenticated_api_client.post(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["deleted_count"] == len(channels)
    assert response.data["deleted_channels"] == [ch.pk for ch in channels]
    channel_objects = Channel.objects.exclude(channel_type=ChannelTypesEnum.MANUAL)
    assert channel_objects.count() == 0
    manual_channel = Channel.objects.get(channel_type=ChannelTypesEnum.MANUAL)
    assert manual_channel.entries.count() == 0
    for entry in deleted_entries + tagged_entries:
        with pytest.raises(Entry.DoesNotExist):
            entry.refresh_from_db()


def test_delete_keep_tagged_not_filtered(db, faker, mocker, authenticated_api_client):
    mocker.patch("kustosz.managers.dispatch_task_by_name")
    all_tags = [w.title() for w in faker.words(nb=5, unique=True)]
    channel_deleted = ChannelFactory.create(active=False, entries=5)
    channel_kept = ChannelFactory.create(active=False, entries=5)
    for entry in channel_deleted.entries.all():
        entry_tags = faker.random.sample(all_tags, k=faker.pyint(max_value=5))
        if not entry_tags:
            continue
        entry.tags.add(*entry_tags)

    url = reverse("channels_delete") + f"?id={channel_deleted.pk}"
    data = {"keep_tagged_entries": False}

    response = authenticated_api_client.post(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["deleted_count"] == 1
    assert response.data["deleted_channels"] == [channel_deleted.pk]
    channel_objects = Channel.objects.exclude(channel_type=ChannelTypesEnum.MANUAL)
    manual_channel = Channel.objects.get(channel_type=ChannelTypesEnum.MANUAL)
    assert channel_objects.count() == 1
    assert channel_kept.entries.count() == 5
    assert manual_channel.entries.count() == 0
