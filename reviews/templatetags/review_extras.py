"""Custom template filters for reviews app."""

from django import template

register = template.Library()


@register.filter(name="mask_middle")
def mask_middle(value: str) -> str:
    """Mask characters except the first and last with asterisks."""
    if not value:
        return ""

    text = str(value)
    if len(text) <= 2:
        return text

    return f"{text[0]}{'*' * (len(text) - 2)}{text[-1]}"
