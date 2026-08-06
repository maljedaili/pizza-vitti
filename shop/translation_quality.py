def _normalized(value):
    return ' '.join((value or '').split()).casefold()


def is_complete_product_translation(translation):
    """A translated product needs real localized copy, not a French fallback clone."""
    if not translation.name.strip() or not translation.description.strip():
        return False
    source = translation.product
    return _normalized(translation.description) != _normalized(source.description)
