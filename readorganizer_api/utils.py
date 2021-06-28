import time
from contextlib import contextmanager

import celery
from django.conf import settings
from django.core.cache import cache
from django.utils.timezone import make_aware


dispatch_task_by_name = celery.current_app.send_task


@contextmanager
def cache_lock(lock_id, our_id):
    timeout = settings.READORGANIZER_LOCK_EXPIRE
    timeout_at = time.monotonic() + timeout
    status = cache.add(lock_id, our_id, timeout)
    try:
        yield status
    finally:
        if time.monotonic() < timeout_at and status:
            cache.delete(lock_id)


def make_unique(sequence):
    return list(dict.fromkeys(sequence))


def optional_make_aware(*args, **kwargs):
    try:
        return make_aware(*args, **kwargs)
    except AttributeError:
        return None
    except ValueError:
        return next(iter(args))
