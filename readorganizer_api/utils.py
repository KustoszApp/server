import time
from contextlib import contextmanager

import celery
from django.conf import settings
from django.core.cache import cache


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
