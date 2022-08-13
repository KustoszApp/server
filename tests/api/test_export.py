from django.urls import reverse
from rest_framework import status

from ..framework.factories.models import ChannelFactory


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
