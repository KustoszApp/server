from django.urls import reverse
from rest_framework import status

from ..framework.factories.models import EntryFilterFactory
from kustosz.enums import EntryFilterActionsEnum


def test_entry_filter_edit(db, faker, authenticated_api_client):
    edited_filter = EntryFilterFactory.create()
    url = reverse("entry_filter_detail", args=[edited_filter.id])
    new_name = faker.text()
    new_condition = "archived=True"
    new_action_name = EntryFilterActionsEnum.ASSIGN_TAG
    new_action_argument = ",".join(faker.words(3))
    data = {
        "name": new_name,
        "condition": new_condition,
        "action_name": new_action_name,
        "action_argument": new_action_argument,
    }

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["name"] == new_name
    assert response.data["name"] != edited_filter.name
    assert response.data["condition"] == new_condition
    assert response.data["condition"] != edited_filter.condition
    assert response.data["action_name"] == new_action_name
    assert response.data["action_name"] != edited_filter.action_name
    assert response.data["action_argument"] == new_action_argument
    assert response.data["action_argument"] != edited_filter.action_argument


def test_entry_filter_edit_enabled(db, faker, authenticated_api_client):
    edited_filter = EntryFilterFactory.create()
    url = reverse("entry_filter_detail", args=[edited_filter.id])
    enabled = False
    data = {"enabled": enabled}

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["enabled"] is False


def test_entry_filter_edit_action_argument_cleaned(db, faker, authenticated_api_client):
    edited_filter = EntryFilterFactory.create(
        action_name=EntryFilterActionsEnum.ASSIGN_TAG,
        action_argument=",".join(faker.words()),
    )
    url = reverse("entry_filter_detail", args=[edited_filter.id])
    new_action_name = EntryFilterActionsEnum.MARK_AS_READ
    data = {
        "action_name": new_action_name,
        "action_argument": "",
    }

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["action_name"] == new_action_name
    assert response.data["action_name"] != edited_filter.action_name
    assert response.data["action_argument"] == ""
    assert response.data["action_argument"] != edited_filter.action_argument


def test_entry_filter_edit_action_argument_left(db, faker, authenticated_api_client):
    edited_filter = EntryFilterFactory.create(
        action_name=EntryFilterActionsEnum.ASSIGN_TAG,
        action_argument=",".join(faker.words()),
    )
    url = reverse("entry_filter_detail", args=[edited_filter.id])
    new_action_name = EntryFilterActionsEnum.MARK_AS_READ
    data = {
        "action_name": new_action_name,
    }

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["action_name"] == new_action_name
    assert response.data["action_name"] != edited_filter.action_name
    assert response.data["action_argument"] == edited_filter.action_argument
    assert response.data["action_argument"] != ""


def test_entry_filter_try_edit_action_argument_not_provided(
    db, faker, authenticated_api_client
):
    old_action_name = EntryFilterActionsEnum.MARK_AS_READ
    edited_filter = EntryFilterFactory.create(action_name=old_action_name)
    url = reverse("entry_filter_detail", args=[edited_filter.id])
    new_action_name = EntryFilterActionsEnum.ASSIGN_TAG
    data = {
        "action_name": new_action_name,
    }

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    edited_filter.refresh_from_db()
    assert edited_filter.action_name == old_action_name
    assert edited_filter.action_name != new_action_name


def test_entry_filter_try_edit_action_argument_empty(
    db, faker, authenticated_api_client
):
    old_action_name = EntryFilterActionsEnum.MARK_AS_READ
    edited_filter = EntryFilterFactory.create(
        action_name=old_action_name,
        action_argument="",
    )
    url = reverse("entry_filter_detail", args=[edited_filter.id])
    new_action_name = EntryFilterActionsEnum.ASSIGN_TAG
    data = {
        "action_name": new_action_name,
        "action_argument": "",
    }

    response = authenticated_api_client.patch(url, data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    edited_filter.refresh_from_db()
    assert edited_filter.action_name == old_action_name
    assert edited_filter.action_name != new_action_name
