from django.core.cache import cache
from django.urls import reverse
from rest_framework import status

from ..framework.factories.models import ChannelFactory
from kustosz.constants import DATA_EXPORT_CACHE_KEY


def test_retrieve_ott(db, faker, authenticated_api_client):
    url = reverse("export_ott")

    response = authenticated_api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert "token" in response.data


def test_channels_opml(db, faker, authenticated_api_client):
    channel_title = faker.sentence()
    channel = ChannelFactory.create(title=channel_title)
    url = reverse("export_channels")

    response = authenticated_api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert "Content-Disposition" in response.headers
    assert "attachment" in response.headers.get("Content-Disposition")
    assert response.headers.get("Content-Type") == "text/xml"
    assert '<opml version="2.0">' in response.data
    assert f'text="{channel.displayed_title}"' in response.data
    assert f'xmlUrl="{channel.url}"' in response.data


def test_channels_opml_token_authentication(
    db, faker, api_client, authenticated_api_client
):
    channel_title = faker.sentence()
    channel = ChannelFactory.create(title=channel_title)
    url = reverse("export_ott")

    response = authenticated_api_client.get(url)
    ott = response.data.get("token")

    url = reverse("export_channels") + f"?token={ott}"
    response = api_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert "Content-Disposition" in response.headers
    assert "attachment" in response.headers.get("Content-Disposition")
    assert response.headers.get("Content-Type") == "text/xml"
    assert '<opml version="2.0">' in response.data
    assert f'text="{channel.displayed_title}"' in response.data
    assert f'xmlUrl="{channel.url}"' in response.data


def test_channels_opml_token_authentication_expired(
    db, api_client, authenticated_api_client
):
    url = reverse("export_ott")

    response = authenticated_api_client.get(url)
    ott = response.data.get("token")

    cache.delete(DATA_EXPORT_CACHE_KEY)

    url = reverse("export_channels") + f"?token={ott}"
    response = api_client.get(url)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_channels_opml_token_authentication_invalid(db, faker, api_client):
    ott = "".join(faker.words())

    url = reverse("export_channels") + f"?token={ott}"
    response = api_client.get(url)

    assert response.status_code == status.HTTP_403_FORBIDDEN
