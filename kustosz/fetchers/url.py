import logging
import re
from html.parser import HTMLParser

from django.conf import settings
from requests import exceptions as requests_exceptions
from requests_cache import CachedSession

from kustosz.constants import FETCHERS_CACHE_DIR
from kustosz.constants import SINGLE_URL_FETCHER_REQUEST_TIMEOUT
from kustosz.exceptions import PermanentFetcherError
from kustosz.exceptions import TransientFetcherError


log = logging.getLogger(__name__)


class EncodingSeekingParser(HTMLParser):
    def reset(self):
        super().reset()
        self.found_encoding = None

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return

        attrs_dict = {key: value for key, value in attrs}
        if meta_charset := attrs_dict.get("charset"):
            self.found_encoding = meta_charset
            return

        if (
            (meta_http_equiv := attrs_dict.get("http-equiv"))
            and meta_http_equiv.lower() == "content-type"
            and (meta_content := attrs_dict.get("content"))
            and "charset" in meta_content
        ):
            charset_re = r"charset=([^ ;\n]+)"
            if m := re.search(charset_re, meta_content):
                self.found_encoding = m.group(1).strip().lower()
            return


class SingleURLFetcher:
    def __init__(self):
        self._session = CachedSession(
            cache_name=(FETCHERS_CACHE_DIR / "http_cache"),
            **settings.KUSTOSZ_REQUESTS_CACHE_INIT_OPTIONS,
        )
        for header, value in settings.KUSTOSZ_URL_FETCHER_EXTRA_HEADERS.items():
            self._session.headers[header] = value
        self._parser = EncodingSeekingParser()

    def _get_content_encoding(self, response):
        # FIXME: implement more exhaustive algorithm from HTML spec?
        # https://html.spec.whatwg.org/multipage/parsing.html#determining-the-character-encoding

        log.debug("Finding encoding of page %s", response.url)

        if "charset" in response.headers.get("Content-Type", ""):
            final_encoding = response.encoding
            log.debug(
                "Encoding set explicitly by server response header: %s [url: '%s']",
                final_encoding,
                response.url,
            )
            return final_encoding

        self._parser.feed(response.content[:1024].decode("ascii", errors="ignore"))
        if final_encoding := self._parser.found_encoding:
            log.debug(
                "Encoding set by meta tag: %s [url: '%s']",
                final_encoding,
                response.url,
            )
            return final_encoding

        final_encoding = response.apparent_encoding
        log.debug(
            "Encoding found by chardet library: %s [url: '%s']",
            final_encoding,
            response.url,
        )
        return final_encoding

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
            raise TransientFetcherError().with_traceback(e.__traceback__) from e
        except (
            requests_exceptions.MissingSchema,
            requests_exceptions.InvalidURL,
            requests_exceptions.InvalidHeader,
            requests_exceptions.InvalidProxyURL,
            requests_exceptions.ContentDecodingError,
        ) as e:
            log.debug("url %s raised %s:", url, e.__class__.__name__, exc_info=True)
            raise PermanentFetcherError().with_traceback(e.__traceback__) from e

        log.debug("url %s returned HTTP code %s", url, response.status_code)

        if not response.ok:
            msg = f"Error code {response.status_code}"
            if 400 <= response.status_code <= 499:
                raise PermanentFetcherError(msg)
            if 500 <= response.status_code <= 599:
                raise TransientFetcherError(msg)

        response.encoding = self._get_content_encoding(response)
        return response

    @classmethod
    def fetch(cls, url: str):
        fetcher = cls()
        response = fetcher._fetch(url)
        return response

    @classmethod
    def clean_cached_files(cls):
        fetcher = cls()
        fetcher._session.remove_expired_responses()
