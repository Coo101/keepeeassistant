"""Filters for the Bootstrap pages (docs/ui-guidelines.md)."""

import datetime

from django import template
from django.forms import BoundField
from django.utils.formats import date_format
from django.utils.safestring import SafeString
from django.utils.translation import get_language

register = template.Library()


@register.filter
def short_date(value: datetime.date, arg: str = "") -> str:
    """A date as "za 1 aug" in Dutch, "Sat 1 Aug" in English; arg "year" adds year."""
    if not value:
        return ""
    language = get_language() or ""
    fmt = "D j b" if language.startswith("nl") else "D j M"
    if arg == "year":
        fmt += " Y"
    return date_format(value, fmt)


@register.filter
def table_input(field: BoundField) -> SafeString:
    """A form field's input for a table cell: Bootstrap classes, and the label as
    aria-label because the label sits in the table header."""
    widget_type = field.widget_type
    if widget_type == "select":
        css = "form-select form-select-sm"
    elif widget_type == "checkbox":
        css = "form-check-input"
    else:
        css = "form-control form-control-sm"
    existing = field.field.widget.attrs.get("class", "")
    if existing:
        css = f"{existing} {css}"
    if field.errors:
        css += " is-invalid"
    return field.as_widget(attrs={"class": css, "aria-label": str(field.label)})
