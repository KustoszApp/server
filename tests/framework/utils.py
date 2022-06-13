from dominate import document
from dominate import tags as t

content_identifier_fields = ("source", "mimetype", "language")


def create_simple_html(title=None, meta=None, body=None):
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
    if body:
        if isinstance(body, t.dom_tag):
            doc.body.add(body)
        else:
            doc.body.add(*body)
    return doc.render(pretty=False)
