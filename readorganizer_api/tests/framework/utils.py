content_identifier_fields = ("source", "mimetype", "language")


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
