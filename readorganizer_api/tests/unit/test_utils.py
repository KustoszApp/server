import pytest
from pytest import approx

from readorganizer_api.utils import estimate_reading_time
from readorganizer_api.utils import normalize_url


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
