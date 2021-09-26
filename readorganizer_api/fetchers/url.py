import logging

from django.conf import settings
from requests import exceptions as requests_exceptions
from requests_cache import CachedSession

from readorganizer_api.constants import FETCHERS_CACHE_DIR
from readorganizer_api.constants import SINGLE_URL_FETCHER_REQUEST_TIMEOUT
from readorganizer_api.exceptions import PermanentFetcherError
from readorganizer_api.exceptions import TransientFetcherError


log = logging.getLogger(__name__)


class SingleURLFetcher:
    def __init__(self):
        self._session = CachedSession(
            cache_name=(FETCHERS_CACHE_DIR / "http_cache"),
            **settings.READORGANIZER_REQUESTS_CACHE_INIT_OPTIONS,
        )

    def _fetch(self, url):
        try:
            response = self._session.get(
                url, timeout=SINGLE_URL_FETCHER_REQUEST_TIMEOUT
            )
        except (
            requests_exceptions.Timeout,
            requests_exceptions.HTTPError,
            requests_exceptions.ConnectionError,
            requests_exceptions.TooManyRedirects,
            requests_exceptions.ChunkedEncodingError,
        ) as e:
            log.debug("url %s raised %s:", url, e.__class__.__name__, exc_info=True)
            raise TransientFetcherError().with_traceback(e.__traceback__)
        except (
            requests_exceptions.MissingSchema,
            requests_exceptions.InvalidURL,
            requests_exceptions.InvalidHeader,
            requests_exceptions.InvalidProxyURL,
            requests_exceptions.ContentDecodingError,
        ) as e:
            log.debug("url %s raised %s:", url, e.__class__.__name__, exc_info=True)
            raise PermanentFetcherError().with_traceback(e.__traceback__)

        log.debug("url %s returned HTTP code %s", url, response.status_code)

        if not response.ok:
            msg = f"Error code {response.status_code}"
            if 400 <= response.status_code <= 499:
                raise PermanentFetcherError(msg)
            if 500 <= response.status_code <= 599:
                raise TransientFetcherError(msg)

        if response.apparent_encoding:
            response.encoding = response.apparent_encoding
        return response

    @classmethod
    def fetch(cls, url: str):
        fetcher = cls()
        response = fetcher._fetch(url)
        return response
