from datetime import datetime

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from ..framework.factories.models import EntryFactory
from readorganizer_api.models import Entry
from readorganizer_api.utils import optional_make_aware


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
