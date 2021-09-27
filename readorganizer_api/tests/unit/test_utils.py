from datetime import datetime

import pytest
from django.utils.http import http_date
from pytest import approx

from ..framework.factories.types import FakeRequestFactory
from ..framework.utils import create_simple_html
from readorganizer_api.utils import estimate_reading_time
from readorganizer_api.utils import normalize_url
from readorganizer_api.utils.extract_metadata import MetadataExtractor


@pytest.mark.parametrize(
    "text,expected",
    [
        pytest.param("", 0, id="empty"),
        pytest.param("single", 0.0043, id="single"),
        pytest.param("word " * 300, 1.3043, id="long string"),
        pytest.param("<a>word</a> " * 300, 1.3043, id="long html"),
    ],
)
def test_estimate_reading_time(text, expected):
    assert estimate_reading_time(text) == approx(expected, rel=1e-4, abs=1e-4)


@pytest.mark.parametrize(
    "url,expected",
    [
        pytest.param("http://test/?utm_source=test", "http://test/", id="utm_source"),
        pytest.param("http://test/?b=2&a=1", "http://test/?a=1&b=2", id="params order"),
        pytest.param(
            "http://test/?a=1&utm_source=test&b=2",
            "http://test/?a=1&b=2",
            id="utm_source between other params",
        ),
        pytest.param("http://TEST.COM/", "http://test.com/", id="lowercased"),
    ],
)
def test_normalize_url_sorted_query(url, expected):
    assert normalize_url(url, sort_query=True) == expected


@pytest.mark.parametrize(
    "url,expected",
    [
        pytest.param("http://test/?b=2&a=1", "http://test/?b=2&a=1", id="params order"),
    ],
)
def test_normalize_url_unsorted_query(url, expected):
    assert normalize_url(url, sort_query=False) == expected


def test_metadata_extract_opengraph(faker):
    metadata = {
        "article:author": faker.name(),
        "og:title": faker.sentence(),
        "article:published_time": faker.iso8601(),
        "article:modified_time": faker.iso8601(),
    }
    html = create_simple_html(meta=metadata)
    resp = FakeRequestFactory(text=html)

    extracted_metadata = MetadataExtractor.from_response(resp)

    assert extracted_metadata.title == metadata["og:title"]
    assert extracted_metadata.author == metadata["article:author"]
    assert extracted_metadata.published_time_upstream == datetime.fromisoformat(
        metadata["article:published_time"]
    )
    assert extracted_metadata.updated_time_upstream == datetime.fromisoformat(
        metadata["article:modified_time"]
    )


def test_metadata_extract_html(faker):
    title = faker.sentence()
    metadata = {"author": faker.name()}
    html = create_simple_html(title=title, meta=metadata)
    resp = FakeRequestFactory(text=html)

    extracted_metadata = MetadataExtractor.from_response(resp)

    assert extracted_metadata.title == title
    assert extracted_metadata.author == metadata["author"]
    assert not extracted_metadata.published_time_upstream
    assert not extracted_metadata.updated_time_upstream


def test_metadata_extract_headers(faker):
    datetime_obj = faker.date_time()
    headers = {
        "Last-Modified": http_date(datetime_obj.timestamp()),
    }
    resp = FakeRequestFactory(headers=headers)

    extracted_metadata = MetadataExtractor.from_response(resp)

    assert extracted_metadata.title
    assert extracted_metadata.author
    assert extracted_metadata.published_time_upstream == datetime_obj
    assert extracted_metadata.updated_time_upstream == datetime_obj


def test_metadata_extract_url(faker):
    url = faker.uri()
    resp = FakeRequestFactory(url=url)

    extracted_metadata = MetadataExtractor.from_response(resp)

    assert extracted_metadata.title == url
    assert extracted_metadata.author
    assert not extracted_metadata.published_time_upstream
    assert not extracted_metadata.updated_time_upstream


def test_metadata_extract_mixed(faker):
    url = faker.uri()
    author = faker.name()
    updated_datetime = faker.date_time()
    metadata = {
        "author": author,
        "article:published_time": faker.iso8601(),
    }
    headers = {
        "Last-Modified": http_date(updated_datetime.timestamp()),
    }
    html = create_simple_html(meta=metadata)
    resp = FakeRequestFactory(url=url, headers=headers, text=html)

    extracted_metadata = MetadataExtractor.from_response(resp)

    assert extracted_metadata.title == url
    assert extracted_metadata.author == author
    assert extracted_metadata.published_time_upstream == datetime.fromisoformat(
        metadata["article:published_time"]
    )
    assert extracted_metadata.updated_time_upstream == updated_datetime
