from django.urls import reverse
from rest_framework import status

import kustosz
from ..framework.factories.models import ChannelFactory
from kustosz.constants import DEFAULT_UPDATE_FREQUENCY
from kustosz.enums import TaskNamesEnum
from kustosz.models import Channel


def test_create_channel(db, faker, mocker, authenticated_api_client):
    mocker.patch("kustosz.managers.dispatch_task_by_name", return_value="1")
    m = Channel.objects
    url = reverse("channels_list")
    new_url = faker.url()
    data = {"url": new_url}

    response = authenticated_api_client.post(url, data)

    assert response.status_code == status.HTTP_201_CREATED
    created_channel = m.last()
    assert created_channel.url == new_url
    kustosz.managers.dispatch_task_by_name.assert_called_once_with(
        TaskNamesEnum.FETCH_FEED_CHANNEL_CONTENT,
        kwargs={"channel_ids": [created_channel.pk], "force_fetch": False},
    )


def test_update_url(db, faker, authenticated_api_client):
    channel = ChannelFactory.create()
    url = reverse("channel_detail", args=[channel.id])
    new_url = faker.url()
    data = {"url": new_url}

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["url"] == new_url
    assert response.data["url"] != channel.url


def test_update_title(db, faker, authenticated_api_client):
    channel = ChannelFactory.create()
    url = reverse("channel_detail", args=[channel.id])
    new_title = faker.text()
    data = {"title": new_title}

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == new_title
    assert response.data["title"] != channel.title


def test_update_active(db, faker, authenticated_api_client):
    channel = ChannelFactory.create(active=True)
    url = reverse("channel_detail", args=[channel.id])
    data = {"active": False}

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["active"] is False
    assert response.data["active"] is not True


def test_update_update_frequency(db, faker, authenticated_api_client):
    channel = ChannelFactory.create()
    url = reverse("channel_detail", args=[channel.id])
    new_update_frequency = faker.random_int(DEFAULT_UPDATE_FREQUENCY + 1)
    data = {"update_frequency": new_update_frequency}

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["update_frequency"] == new_update_frequency
    assert response.data["update_frequency"] > channel.update_frequency


def test_tags_in_list(db, faker, authenticated_api_client):
    tags = [w.title() for w in faker.words(unique=True)]
    channel = ChannelFactory.create(tags=tags)
    url = reverse("channels_list")

    response = authenticated_api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert set(response.data["results"][0]["tags"]) == set(channel.tags.names())
    assert set(response.data["results"][0]["tags"]) == set(tags)


def test_add_tags(db, faker, authenticated_api_client):
    channel = ChannelFactory.create()
    url = reverse("channel_detail", args=[channel.id])
    new_tags = faker.words(unique=True)
    data = {"tags": new_tags}

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert set(response.data["tags"]) == set(channel.tags.names())
    assert set(response.data["tags"]) == set(new_tags)


def test_remove_tags(db, faker, authenticated_api_client):
    old_tags = faker.words(unique=True)
    channel = ChannelFactory.create(tags=old_tags)
    url = reverse("channel_detail", args=[channel.id])
    data = {"tags": []}

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["tags"] == []
    assert set(response.data["tags"]) != set(old_tags)


def test_set_tags(db, faker, authenticated_api_client):
    old_tags = faker.words(unique=True)
    channel = ChannelFactory.create(tags=old_tags)
    url = reverse("channel_detail", args=[channel.id])
    new_tags = faker.words(unique=True)
    data = {"tags": new_tags}

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert set(response.data["tags"]) == set(channel.tags.names())
    assert set(response.data["tags"]) == set(new_tags)
    assert set(response.data["tags"]) != set(old_tags)
