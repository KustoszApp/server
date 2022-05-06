from datetime import datetime

from django.urls import reverse
from rest_framework import status

import kustosz
from ..framework.factories.models import EntryContentFactory
from ..framework.factories.models import EntryFactory
from kustosz.enums import ChannelTypesEnum
from kustosz.models import Channel
from kustosz.models import Entry
from kustosz.utils import optional_make_aware


def test_list_content(db, authenticated_api_client):
    EntryFactory.create(content_set=3)
    url = reverse("entries_list")

    response = authenticated_api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    response_entry = response.data["results"][0]
    assert len(response_entry["available_contents"]) == 3
    for key in (
        "id",
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


def test_detail_content(db, authenticated_api_client):
    entry = EntryFactory.create(content_set=3)
    url = reverse("entry_detail", args=[entry.id])

    response = authenticated_api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["contents"]) == 3
    for key in (
        "id",
        "source",
        "content",
        "mimetype",
        "language",
        "estimated_reading_time",
        "updated_time",
    ):
        assert key in response.data["contents"][0]
        assert key in response.data["preferred_content"]


def test_archive_entry(db, authenticated_api_client):
    entry = EntryFactory.create()
    url = reverse("entry_detail", args=[entry.id])
    data = {"archived": True}

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["archived"] is True
    updated_time = optional_make_aware(
        datetime.strptime(response.data["updated_time"], "%Y-%m-%dT%H:%M:%S.%fZ")
    )
    assert updated_time > entry.updated_time
    entry.refresh_from_db()
    assert entry.archived is True


def test_unarchive_entry(db, authenticated_api_client):
    entry = EntryFactory.create(archived=True)
    url = reverse("entry_detail", args=[entry.id])
    data = {"archived": False}

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["archived"] is False
    updated_time = optional_make_aware(
        datetime.strptime(response.data["updated_time"], "%Y-%m-%dT%H:%M:%S.%fZ")
    )
    assert updated_time > entry.updated_time
    entry.refresh_from_db()
    assert entry.archived is False


def test_mass_archive_entries(db, authenticated_api_client):
    entries = EntryFactory.create_batch(5)
    url = reverse("entries_archive") + "?archived=0"

    response = authenticated_api_client.post(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["archived_count"] == 5
    assert response.data["archived_entries"] == list(range(1, 6))
    assert not Entry.objects.filter(archived=False)
    assert Entry.objects.filter(archived=True).count() == 5
    assert Entry.objects.first().updated_time > entries[0].updated_time


def test_mass_archive_entries_subset(db, authenticated_api_client):
    entries = EntryFactory.create_batch(5)
    entry_to_update = entries[2]
    url = reverse("entries_archive") + f"?channel={entry_to_update.channel.pk}"

    response = authenticated_api_client.post(url)

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


def test_set_preferred_content(db, authenticated_api_client):
    entry = EntryFactory.create(content_set=3)
    url = reverse("entry_detail", args=[entry.id])
    old_preferred_content = entry.preferred_content
    new_preferred_content = entry.content_set.order_by("estimated_reading_time").first()
    data = {"preferred_content": new_preferred_content.pk}

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    response_data = response.data["preferred_content"]
    for key in (
        "id",
        "content",
        "estimated_reading_time",
    ):
        assert response_data[key] == getattr(new_preferred_content, key)
        assert response_data[key] != getattr(old_preferred_content, key)


def test_try_setting_existing_preferred_content_belonging_to_other_entry(
    db, authenticated_api_client
):
    entry = EntryFactory.create(content_set=3)
    another_entry = EntryFactory.create(content_set=1)
    url = reverse("entry_detail", args=[entry.id])
    old_preferred_content = entry.preferred_content
    new_preferred_content = another_entry.preferred_content
    data = {"preferred_content": new_preferred_content.pk}

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    entry.refresh_from_db()
    assert entry.preferred_content == old_preferred_content
    assert entry.preferred_content != new_preferred_content


def test_try_setting_non_existing_preferred_content(db, authenticated_api_client):
    entry = EntryFactory.create(content_set=3)
    url = reverse("entry_detail", args=[entry.id])
    old_preferred_content = entry.preferred_content
    new_preferred_content = EntryContentFactory.build()
    data = {"preferred_content": new_preferred_content.pk}

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    entry.refresh_from_db()
    assert entry.preferred_content == old_preferred_content
    assert entry.preferred_content != new_preferred_content


def test_try_setting_preferred_content_invalid_input_missing_required_field(
    db, authenticated_api_client
):
    entry = EntryFactory.create(content_set=3)
    url = reverse("entry_detail", args=[entry.id])
    old_preferred_content = entry.preferred_content
    data = {"preferred_content": None}

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    entry.refresh_from_db()
    assert entry.preferred_content == old_preferred_content


def test_add_tags(db, faker, authenticated_api_client):
    entry = EntryFactory.create()
    url = reverse("entry_detail", args=[entry.id])
    new_tags = faker.words(unique=True)
    data = {"tags": new_tags}

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert set(response.data["tags"]) == set(entry.tags.names())
    assert set(response.data["tags"]) == set(new_tags)


def test_remove_tags(db, faker, authenticated_api_client):
    old_tags = faker.words(unique=True)
    entry = EntryFactory.create(tags=old_tags)
    url = reverse("entry_detail", args=[entry.id])
    data = {"tags": []}

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["tags"] == []
    assert set(response.data["tags"]) != set(old_tags)


def test_set_tags(db, faker, authenticated_api_client):
    old_tags = faker.words(unique=True)
    entry = EntryFactory.create(tags=old_tags)
    url = reverse("entry_detail", args=[entry.id])
    new_tags = faker.words(unique=True)
    data = {"tags": new_tags}

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert set(response.data["tags"]) == set(entry.tags.names())
    assert set(response.data["tags"]) == set(new_tags)
    assert set(response.data["tags"]) != set(old_tags)


def test_filter_tags_return_unique_entries(db, faker, authenticated_api_client):
    tags = faker.words(unique=True)
    EntryFactory.create(tags=tags)
    url = reverse("entries_list") + f"?tags={','.join(tags)}"

    response = authenticated_api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert len(response.data["results"]) == 1


def test_entry_add_manually(db, mocker, faker, authenticated_api_client):
    mocker.patch("kustosz.managers.dispatch_task_by_name")
    entry_url = faker.uri()
    url = reverse("entry_manual_add")
    data = {"link": entry_url}

    response = authenticated_api_client.post(url, data)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["link"] == entry_url
    assert kustosz.managers.dispatch_task_by_name.called


def test_entry_try_add_manually_invalid_url(
    db, mocker, faker, authenticated_api_client
):
    mocker.patch("kustosz.managers.dispatch_task_by_name")
    entry_url = faker.text()
    url = reverse("entry_manual_add")
    data = {"link": entry_url}

    response = authenticated_api_client.post(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["link"] != entry_url
    assert not kustosz.managers.dispatch_task_by_name.called


def test_entry_try_add_manually_already_exists(
    db, mocker, faker, authenticated_api_client
):
    mocker.patch("kustosz.managers.dispatch_task_by_name")
    manual_channel = Channel.objects.filter(
        channel_type=ChannelTypesEnum.MANUAL
    ).first()
    gid = faker.uri()
    entry = EntryFactory.create(channel=manual_channel, gid=gid, link=gid)
    url = reverse("entry_manual_add")
    data = {"link": entry.link}

    response = authenticated_api_client.post(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert any("already exists" in error for error in response.data)
    assert not kustosz.managers.dispatch_task_by_name.called


def test_entry_try_add_manually_link_already_exists(
    db, mocker, faker, authenticated_api_client
):
    mocker.patch("kustosz.managers.dispatch_task_by_name")
    manual_channel = Channel.objects.filter(
        channel_type=ChannelTypesEnum.MANUAL
    ).first()
    gid = faker.uri()
    link = faker.uri()
    entry = EntryFactory.create(channel=manual_channel, gid=gid, link=link)
    url = reverse("entry_manual_add")
    data = {"link": entry.link}

    response = authenticated_api_client.post(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert any("already exists" in error for error in response.data)
    assert not kustosz.managers.dispatch_task_by_name.called


def test_entry_add_manually_cors(db, mocker, faker, authenticated_api_client):
    mocker.patch("kustosz.managers.dispatch_task_by_name")
    origin = faker.url()
    url = reverse("entry_manual_add")
    extra_headers = {
        "HTTP_ACCESS_CONTROL_REQUEST_METHOD": "POST",
        "HTTP_ORIGIN": origin,
    }

    response = authenticated_api_client.options(url, data=None, **extra_headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.headers.get("Access-Control-Allow-Origin") == origin
    assert not kustosz.managers.dispatch_task_by_name.called
