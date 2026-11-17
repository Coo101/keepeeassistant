"""core.htmx.render_page_or_fragment: the fragment for HTMX, the page otherwise."""

import pytest
from django.test import RequestFactory, override_settings
from django_htmx.middleware import HtmxDetails

from core.htmx import render_page_or_fragment

LOCMEM_TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "OPTIONS": {
            "loaders": [
                (
                    "django.template.loaders.locmem.Loader",
                    {"page.html": "PAGE", "frag.html": "FRAG {{ is_fragment }}"},
                )
            ]
        },
    }
]

pytestmark = pytest.mark.usefixtures("locmem_templates")


@pytest.fixture
def locmem_templates():
    with override_settings(TEMPLATES=LOCMEM_TEMPLATES):
        yield


def _render(**headers: str):
    request = RequestFactory().get("/", headers=headers)
    request.htmx = HtmxDetails(request)
    return render_page_or_fragment(request, "page.html", "frag.html", {})


def test_plain_request_gets_the_page() -> None:
    assert _render().content == b"PAGE"


def test_htmx_request_gets_the_fragment() -> None:
    assert _render(**{"HX-Request": "true"}).content == b"FRAG True"


def test_history_restore_gets_the_page() -> None:
    response = _render(**{"HX-Request": "true", "HX-History-Restore-Request": "true"})
    assert response.content == b"PAGE"


def test_response_varies_on_hx_request() -> None:
    assert "HX-Request" in _render()["Vary"]
