"""PDF rendering via WeasyPrint, with graceful HTML fallback (SPEC §9.5).

WeasyPrint needs the GTK/Pango native libraries; on machines without them we
serve the same template as a print-friendly HTML page instead of a PDF.
"""

import functools
import logging

from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@functools.cache
def weasyprint_available() -> bool:
    try:
        import weasyprint  # noqa: F401
    except (ImportError, OSError) as exc:
        logger.warning("WeasyPrint unavailable, falling back to HTML: %s", exc)
        return False
    return True


def render_pdf(
    request: HttpRequest, template: str, context: dict, filename: str
) -> HttpResponse:
    """Render a template to a PDF download, or to printable HTML as fallback."""
    if not weasyprint_available():
        context = {**context, "pdf_fallback": True}
        return HttpResponse(render_to_string(template, context, request))

    from weasyprint import HTML

    html = render_to_string(template, context, request)
    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response
