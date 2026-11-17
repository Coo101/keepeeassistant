"""Render a whole page, or only its swapped fragment for an HTMX request.

See docs/ui-guidelines.md, "HTMX patterns": the same URL serves both, so a live
search or a live scale also works as a plain GET without JavaScript.
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.cache import patch_vary_headers


def render_page_or_fragment(
    request: HttpRequest, page: str, fragment: str, context: dict
) -> HttpResponse:
    """The fragment for an HTMX request, the page otherwise.

    A history-restore request (Back after a pushed URL) gets the page, and the
    response varies on HX-Request so the browser cache never serves the fragment
    as the page.
    """
    htmx = getattr(request, "htmx", None)
    is_fragment = bool(htmx) and not htmx.history_restore_request
    response = render(
        request,
        fragment if is_fragment else page,
        {**context, "is_fragment": is_fragment},
    )
    patch_vary_headers(response, ("HX-Request", "HX-History-Restore-Request"))
    return response
