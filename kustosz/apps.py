from django.apps import AppConfig


class KustoszConfig(AppConfig):
    name = "kustosz"

    def ready(self):
        from . import signals  # noqa
