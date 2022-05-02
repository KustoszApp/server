import pytest

from ..framework.factories.types import FakeRequestFactory
from kustosz.fetchers.url import EncodingSeekingParser
from kustosz.fetchers.url import SingleURLFetcher


@pytest.mark.parametrize(
    "text,expected",
    [
        pytest.param(
            '<html><head><meta charset="iso-8859-2" />', "iso-8859-2", id="meta_charset"
        ),
        pytest.param(
            '<html><head><meta http-equiv="Content-Type" content="text/html; charset=cp-1250" />',  # noqa
            "cp-1250",
            id="meta_http_equiv",
        ),
        pytest.param(
            '<html><head><meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-13; boundary=something" />',  # noqa
            "iso-8859-13",
            id="http_equiv_first",
        ),
        pytest.param(
            '<html><head><meta http-equiv="Content-Type" content="text/html; boundary=something; charset=euc-jp" />',  # noqa
            "euc-jp",
            id="http_equiv_last",
        ),
        pytest.param(
            "<html><head><title>Test</title></head></html>", "", id="no_meta_tag"
        ),
        pytest.param(
            '<html><head><meta http-equiv="Content-Security-Policy" content="default-src; font-src" />',  # noqa
            "",
            id="http_equiv_not_content_type",
        ),
        pytest.param(
            '<html><head><meta http-equiv="Content-Type" />',
            "",
            id="http_equiv_no_content",
        ),
        pytest.param(
            '<html><head><meta http-equiv="Content-Type" content="text/html" />',
            "",
            id="http_equiv_no_charset",
        ),
        pytest.param(
            '<html><head><meta http-equiv="Content-Type" content="text/html; charset=" />',  # noqa
            "",
            id="http_equiv_no_charset_value",
        ),
    ],
)
def test_encoding_seeking_parser(text, expected):
    parser = EncodingSeekingParser()
    parser.feed(text)
    found = parser.found_encoding
    if expected:
        assert found == expected
    else:
        assert found is None


@pytest.mark.parametrize(
    "fake_request,expected",
    [
        pytest.param(
            FakeRequestFactory(
                headers={"Content-Type": "text/html; charset=utf-8"},
                content='<html><head><meta charset="iso-8859-2">'.encode("ascii"),
                apparent_encoding="cp-1250",
            ),
            "utf-8",
            id="http_header",
        ),
        pytest.param(
            FakeRequestFactory(
                headers={"Content-Type": "text/html"},
                content='<html><head><meta charset="iso-8859-2">'.encode("ascii"),
                apparent_encoding="cp-1250",
            ),
            "iso-8859-2",
            id="content_meta",
        ),
        pytest.param(
            FakeRequestFactory(
                headers={"Content-Type": "text/html"},
                content="<html>".encode("ascii"),
                apparent_encoding="cp-1250",
            ),
            "cp-1250",
            id="apparent_encoding",
        ),
    ],
)
def test_fetched_url_encoding(fake_request, expected, mocker):
    mocker.patch("kustosz.fetchers.url.CachedSession.get", return_value=fake_request)
    response = SingleURLFetcher.fetch("http://example.com")
    assert response.encoding == expected
    encodings = [
        encoding
        for encoding in ("utf-8", "iso-8859-2", "cp-1250")
        if encoding != expected
    ]
    for encoding in encodings:
        assert response.encoding != encoding
