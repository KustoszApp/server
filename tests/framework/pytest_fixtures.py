import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from kustosz.models import User


@pytest.fixture()
def user_model(faker, db):
    name = f"test-{faker.user_name()}"
    passwd = faker.pystr(20)
    user = User.objects.create(username=name, password=passwd)
    yield user


@pytest.fixture()
def api_client():
    yield APIClient()


@pytest.fixture()
def authenticated_api_client(user_model, api_client):
    token = Token.objects.create(user=user_model)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    yield api_client
