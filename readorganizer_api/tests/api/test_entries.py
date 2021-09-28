from datetime import datetime

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

import readorganizer_api
from ..framework.factories.models import EntryContentFactory
from ..framework.factories.models import EntryFactory
from ..framework.utils import get_content_identifier
from readorganizer_api.enums import ChannelTypesEnum
from readorganizer_api.models import Channel
from readorganizer_api.models import Entry
from readorganizer_api.utils import optional_make_aware


def test_list_content(db):
    EntryFactory.create(content_set=3)
    client = APIClient()
    url = reverse("entries_list")

    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    response_entry = response.data["results"][0]
    assert len(response_entry["available_contents"]) == 3
    for key in (
        "source",
        "mimetype",
        "language",
        "estimated_reading_time",
        "updated_time",
    ):
        assert key in response_entry["available_contents"][0]
        assert key in response_entry["preferred_content"]
    assert "content" not in response_entry["available_contents"][0]
    assert "content" in response_entry["preferred_content"]


def test_detail_content(db):
    entry = EntryFactory.create(content_set=3)
    client = APIClient()
    url = reverse("entry_detail", args=[entry.id])

    response = client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["contents"]) == 3
    for key in (
        "source",
        "content",
        "mimetype",
        "language",
        "estimated_reading_time",
        "updated_time",
    ):
        assert key in response.data["contents"][0]
        assert key in response.data["preferred_content"]


def test_archive_entry(db):
    entry = EntryFactory.create()
    client = APIClient()
    url = reverse("entry_detail", args=[entry.id])
    data = {"archived": True}

    response = client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["archived"] is True
    updated_time = optional_make_aware(
        datetime.strptime(response.data["updated_time"], "%Y-%m-%dT%H:%M:%S.%fZ")
    )
    assert updated_time > entry.updated_time
    entry.refresh_from_db()
    assert entry.archived is True


def test_unarchive_entry(db):
    entry = EntryFactory.create(archived=True)
    client = APIClient()
    url = reverse("entry_detail", args=[entry.id])
    data = {"archived": False}

    response = client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["archived"] is False
    updated_time = optional_make_aware(
        datetime.strptime(response.data["updated_time"], "%Y-%m-%dT%H:%M:%S.%fZ")
    )
    assert updated_time > entry.updated_time
    entry.refresh_from_db()
    assert entry.archived is False


def test_mass_archive_entries(db):
    entries = EntryFactory.create_batch(5)
    client = APIClient()
    url = reverse("entries_archive") + "?archived=0"

    response = client.post(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["archived_count"] == 5
    assert response.data["archived_entries"] == list(range(1, 6))
    assert not Entry.objects.filter(archived=False)
    assert Entry.objects.filter(archived=True).count() == 5
    assert Entry.objects.first().updated_time > entries[0].updated_time


def test_mass_archive_entries_subset(db):
    entries = EntryFactory.create_batch(5)
    entry_to_update = entries[2]
    client = APIClient()
    url = reverse("entries_archive") + f"?channel={entry_to_update.channel.pk}"

    response = client.post(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["archived_count"] == 1
    assert response.data["archived_entries"] == [entry_to_update.pk]
    assert Entry.objects.filter(archived=False).count() == 4
    assert Entry.objects.filter(archived=True).count() == 1
    assert Entry.objects.first().updated_time == entries[0].updated_time
    assert (
        Entry.objects.filter(pk=entry_to_update.pk).first().updated_time
        > entry_to_update.updated_time
    )  # noqa


def test_set_preferred_content(db):
    entry = EntryFactory.create(content_set=3)
    client = APIClient()
    url = reverse("entry_detail", args=[entry.id])
    old_preferred_content = entry.preferred_content
    new_preferred_content = entry.content_set.order_by("estimated_reading_time").first()
    data = {
        "preferred_content": get_content_identifier(new_preferred_content, as_dict=True)
    }

    response = client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    old_values = get_content_identifier(old_preferred_content)
    new_values = get_content_identifier(new_preferred_content)
    received_values = get_content_identifier(response.data["preferred_content"])
    assert received_values == new_values
    assert received_values != old_values
    response_data = response.data["preferred_content"]
    for key in (
        "content",
        "estimated_reading_time",
    ):
        assert response_data[key] == getattr(new_preferred_content, key)
        assert response_data[key] != getattr(old_preferred_content, key)


def test_try_setting_non_existing_preferred_content(db):
    entry = EntryFactory.create(content_set=3)
    client = APIClient()
    url = reverse("entry_detail", args=[entry.id])
    old_preferred_content = entry.preferred_content
    new_preferred_content = EntryContentFactory.build()
    data = {
        "preferred_content": get_content_identifier(new_preferred_content, as_dict=True)
    }

    response = client.patch(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    entry.refresh_from_db()
    old_values = get_content_identifier(old_preferred_content)
    new_values = get_content_identifier(new_preferred_content)
    db_values = get_content_identifier(entry.preferred_content)
    assert db_values != new_values
    assert db_values == old_values


def test_try_setting_preferred_content_invalid_input_missing_required_field(db):
    entry = EntryFactory.create(content_set=3)
    client = APIClient()
    url = reverse("entry_detail", args=[entry.id])
    old_preferred_content = entry.preferred_content
    new_preferred_content = entry.content_set.first()
    new_payload = get_content_identifier(new_preferred_content, as_dict=True)
    new_payload.pop("source")
    data = {"preferred_content": new_payload}

    response = client.patch(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    entry.refresh_from_db()
    old_values = get_content_identifier(old_preferred_content)
    new_values = get_content_identifier(new_preferred_content)
    db_values = get_content_identifier(entry.preferred_content)
    assert db_values != new_values
    assert db_values == old_values


def test_add_tags(db, faker):
    entry = EntryFactory.create()
    client = APIClient()
    url = reverse("entry_detail", args=[entry.id])
    new_tags = faker.words(unique=True)
    data = {"tags": new_tags}

    response = client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert set(response.data["tags"]) == set(entry.tags.names())
    assert set(response.data["tags"]) == set(new_tags)


def test_remove_tags(db, faker):
    old_tags = faker.words(unique=True)
    entry = EntryFactory.create(tags=old_tags)
    client = APIClient()
    url = reverse("entry_detail", args=[entry.id])
    data = {"tags": []}

    response = client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["tags"] == []
    assert set(response.data["tags"]) != set(old_tags)


def test_set_tags(db, faker):
    old_tags = faker.words(unique=True)
    entry = EntryFactory.create(tags=old_tags)
    client = APIClient()
    url = reverse("entry_detail", args=[entry.id])
    new_tags = faker.words(unique=True)
    data = {"tags": new_tags}

    response = client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert set(response.data["tags"]) == set(entry.tags.names())
    assert set(response.data["tags"]) == set(new_tags)
    assert set(response.data["tags"]) != set(old_tags)


def test_entry_add_manually(db, mocker, faker):
    mocker.patch("readorganizer_api.managers.dispatch_task_by_name")
    entry_url = faker.url()
    client = APIClient()
    url = reverse("entry_manual_add")
    data = {"link": entry_url}

    response = client.post(url, data)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["link"] == entry_url
    assert readorganizer_api.managers.dispatch_task_by_name.called


def test_entry_try_add_manually_invalid_url(db, mocker, faker):
    mocker.patch("readorganizer_api.managers.dispatch_task_by_name")
    entry_url = faker.text()
    client = APIClient()
    url = reverse("entry_manual_add")
    data = {"link": entry_url}

    response = client.post(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["link"] != entry_url
    assert not readorganizer_api.managers.dispatch_task_by_name.called


def test_entry_try_add_manually_already_exists(db, mocker, faker):
    mocker.patch("readorganizer_api.managers.dispatch_task_by_name")
    manual_channel = Channel.objects.filter(
        channel_type=ChannelTypesEnum.MANUAL
    ).first()
    gid = faker.url()
    entry = EntryFactory.create(channel=manual_channel, gid=gid, link=gid)
    client = APIClient()
    url = reverse("entry_manual_add")
    data = {"link": entry.link}

    response = client.post(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not readorganizer_api.managers.dispatch_task_by_name.called
