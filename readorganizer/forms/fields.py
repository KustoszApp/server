from django.forms.fields import URLField

from readorganizer.validators import ChannelURLValidator


class ChannelURLFormField(URLField):
    default_validators = [ChannelURLValidator()]
