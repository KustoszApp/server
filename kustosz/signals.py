from corsheaders.signals import check_request_enabled
from django.urls import reverse_lazy


def cors_check_request_enabled_receiver(sender, **kwargs):
    entry_manual_add_url = reverse_lazy("entry_manual_add")
    current_url = kwargs.get("request").path
    return current_url == entry_manual_add_url


check_request_enabled.connect(
    cors_check_request_enabled_receiver, dispatch_uid="kustosz_manual_add_entry"
)
