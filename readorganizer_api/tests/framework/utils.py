from dominate import document
from dominate import tags as t

content_identifier_fields = ("source", "mimetype", "language")


def create_simple_html(title=None, meta=None):
    doc = document()
    if title:
        doc.title = title
    else:
        old_title = doc.head.children[0]
        doc.head.remove(old_title)
    if meta:
        for key, value in meta.items():
            if key.startswith(("og:", "article:")):
                elem = t.meta(property=key, content=value)
            else:
                elem = t.meta(name=key, content=value)
            doc.head += elem
    return doc.render(pretty=False)


def get_content_identifier(obj_or_dict, as_dict=False):
    rv = {}
    for key in content_identifier_fields:
        try:
            value = getattr(obj_or_dict, key)
        except AttributeError:
            value = obj_or_dict.get(key)
        rv[key] = value
    if as_dict:
        return rv
    return tuple(rv.values())
