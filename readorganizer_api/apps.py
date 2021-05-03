from django.apps import AppConfig


class ReadOrganizerApiConfig(AppConfig):
    name = "readorganizer_api"

    def ready(self):
        import readorganizer_api.signals  # noqa: F401
