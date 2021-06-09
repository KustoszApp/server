from django.forms.fields import URLField

from readorganizer_api.validators import ChannelURLValidator


class ChannelURLFormField(URLField):
    default_validators = [ChannelURLValidator()]
