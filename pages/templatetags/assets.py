"""Static URLs that change when the file changes, so browsers never keep an old copy."""

from pathlib import Path

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def asset(path: str) -> str:
    """URL of a static file, with its modification time as a version in debug mode.

    The dev server sends no cache header, so browsers guess how long to keep a file and
    can show an old stylesheet for hours. In production the manifest storage already
    puts a hash in the file name.
    """
    url = static(path)
    if not settings.DEBUG:
        return url
    found = finders.find(path)
    if not found:
        return url
    return f"{url}?v={int(Path(found).stat().st_mtime)}"
