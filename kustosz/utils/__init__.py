import time
from contextlib import contextmanager
from functools import lru_cache
from operator import itemgetter

import celery
import hyperlink
import unalix
from django.conf import settings
from django.core.cache import cache
from django.utils.html import strip_tags
from django.utils.timezone import make_aware

dispatch_task_by_name = celery.current_app.send_task


@contextmanager
def cache_lock(lock_id, our_id):
    timeout = settings.KUSTOSZ_LOCK_EXPIRE
    timeout_at = time.monotonic() + timeout
    status = cache.add(lock_id, our_id, timeout)
    try:
        yield status
    finally:
        if time.monotonic() < timeout_at and status:
            cache.delete(lock_id)


@lru_cache
def estimate_reading_time(text: str) -> float:
    text = strip_tags(text)
    num_words = len(text.split())
    minutes = num_words / settings.KUSTOSZ_READING_SPEED_WPM
    return minutes


def make_unique(sequence):
    return list(dict.fromkeys(sequence))


@lru_cache
def normalize_url(url: str, sort_query: bool = True) -> str:
    cleared_url = unalix.clear_url(url)
    parsed_url = hyperlink.parse(cleared_url).normalize()
    if sort_query:
        query = sorted(parsed_url.query, key=itemgetter(0))
        parsed_url = parsed_url.replace(query=query)
    return parsed_url.to_text()


def optional_make_aware(*args, **kwargs):
    try:
        return make_aware(*args, **kwargs)
    except AttributeError:
        return None
    except ValueError:
        return next(iter(args))
