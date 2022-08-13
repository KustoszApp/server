from django.core.cache import cache
from rest_framework import authentication
from rest_framework import exceptions

from kustosz.constants import DATA_EXPORT_CACHE_KEY
from kustosz.models import User


invalid_token_msg = "Invalid token provided"


class ExportOTTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        ott = request.query_params.get("token")
        if not ott:
            return None

        stored_ott = cache.get(DATA_EXPORT_CACHE_KEY)
        if not stored_ott:
            raise exceptions.AuthenticationFailed(invalid_token_msg)

        cache.delete(DATA_EXPORT_CACHE_KEY)
        if stored_ott != ott:
            raise exceptions.AuthenticationFailed(invalid_token_msg)

        user = User.objects.last()
        return (user, None)
