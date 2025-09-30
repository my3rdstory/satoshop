"""Custom template filters for reviews app."""

import bleach
from bleach.linkifier import Linker
from django import template
from django.utils.safestring import mark_safe

from reviews.services import find_x_post_url


register = template.Library()


def _set_external_link_attrs(attrs, new=False):  # pylint: disable=unused-argument
    attrs[(None, 'target')] = '_blank'
    rel = attrs.get((None, 'rel'), '') or ''
    rel_tokens = {token for token in rel.split() if token}
    rel_tokens.update({'noopener', 'noreferrer'})
    attrs[(None, 'rel')] = ' '.join(sorted(rel_tokens))
    return attrs


_review_linker = Linker(callbacks=[_set_external_link_attrs], skip_tags=['a'])


@register.filter(name="mask_middle")
def mask_middle(value: str) -> str:
    """Mask characters except the first and last with asterisks."""
    if not value:
        return ""

    text = str(value)
    if len(text) <= 2:
        return text

    return f"{text[0]}{'*' * (len(text) - 2)}{text[-1]}"


@register.filter(name="first_x_post_url")
def first_x_post_url(value: str) -> str:
    """Extract the first X/Twitter status URL from text if available."""
    return find_x_post_url(value or '') or ''


@register.filter(name="linkify_review")
def linkify_review(value: str) -> str:
    """Sanitize review text and convert URLs to external links."""
    if not value:
        return ''

    cleaned = bleach.clean(value, tags=[], strip=True)
    linked = _review_linker.linkify(cleaned)
    return mark_safe(linked)
