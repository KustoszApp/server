from rest_framework import renderers


class RawDataRenderer(renderers.BaseRenderer):
    media_type = "text/xml"
    format = "xml"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data
