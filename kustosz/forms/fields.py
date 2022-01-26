from django.forms.fields import URLField

from kustosz.validators import ChannelURLValidator


class ChannelURLFormField(URLField):
    default_validators = [ChannelURLValidator()]
