from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .framework.factories.models import EntryFactory


def test_archive_entry(db):
    entry = EntryFactory.create()
    client = APIClient()
    url = reverse("entry_detail", args=[entry.id])
    data = {"archived": True}

    response = client.patch(url, data)

    entry.refresh_from_db()
    assert response.status_code == status.HTTP_200_OK
    assert response.data["archived"] is True
    assert entry.archived is True


def test_unarchive_entry(db):
    entry = EntryFactory.create(archived=True)
    client = APIClient()
    url = reverse("entry_detail", args=[entry.id])
    data = {"archived": False}

    response = client.patch(url, data)

    entry.refresh_from_db()
    assert response.status_code == status.HTTP_200_OK
    assert response.data["archived"] is False
    assert entry.archived is False
