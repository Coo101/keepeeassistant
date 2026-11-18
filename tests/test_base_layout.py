"""The shared layout on Bootstrap and HTMX (docs/SPEC.md, docs/ui-guidelines.md)."""

import re

import pytest
from django.contrib import messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.template.loader import render_to_string
from django.test import Client, RequestFactory
from django.urls import reverse

from tests.factories import account_client

pytestmark = pytest.mark.django_db


def test_pages_load_the_vendored_assets_and_htmx_csrf_header() -> None:
    html = account_client().get(reverse("camp_list")).content.decode()
    assert "vendor/bootstrap/css/bootstrap.min.css" in html
    assert "vendor/bootstrap/js/bootstrap.bundle.min.js" in html
    assert "vendor/htmx/htmx.min.js" in html
    assert 'hx-headers=\'{"X-CSRFToken": "' in html
    assert 'id="main-nav"' in html


def test_navbar_marks_the_current_language() -> None:
    html = Client(headers={"accept-language": "en"}).get("/").content.decode()
    assert 'fw-bold" type="submit" name="language" value="en"' in html
    assert 'fw-bold" type="submit" name="language" value="nl"' not in html


def test_messages_render_as_dismissible_alerts() -> None:
    request = RequestFactory().get("/")
    request.session = {}
    request._messages = FallbackStorage(request)
    messages.error(request, "Something went wrong")
    messages.success(request, "Saved")

    html = render_to_string("components/messages.html", request=request)

    assert 'class="alert alert-danger alert-dismissible' in html
    assert 'class="alert alert-success alert-dismissible' in html
    assert "Something went wrong" in html
    assert 'data-bs-dismiss="alert"' in html


def test_messages_show_once_on_the_account_page() -> None:
    response = account_client().post(
        reverse("account"),
        {"first_name": "Kok", "last_name": "", "email": ""},
        headers={"accept-language": "en"},
        follow=True,
    )
    assert response.content.decode().count("Your details were saved.") == 1


def test_navbar_is_chiro_red_with_the_egg_icon() -> None:
    html = account_client().get(reverse("camp_list")).content.decode()
    assert "navbar-chiro" in html
    assert "bi-egg-fried" in html
    assert "🏕️" not in html


def test_camp_list_has_one_h1_and_the_red_rule() -> None:
    html = account_client().get(reverse("camp_list")).content.decode()
    assert "page-rule" in html
    assert html.count("<h1") == 1


def test_navbar_marks_only_the_current_page() -> None:
    html = account_client().get(reverse("camp_list")).content.decode()
    assert f'href="{reverse("camp_list")}" aria-current="page"' in html
    assert f'href="{reverse("recipe_list")}" aria-current="page"' not in html
    assert html.count('aria-current="page"') == 1


def test_stylesheet_url_changes_with_the_file_in_debug(settings) -> None:
    from pages.templatetags.assets import asset

    settings.DEBUG = True
    assert re.fullmatch(r"/static/css/app\.css\?v=\d+", asset("css/app.css"))
    settings.DEBUG = False
    assert asset("css/app.css") == "/static/css/app.css"


def test_pages_link_the_versioned_stylesheet(settings) -> None:
    settings.DEBUG = True
    html = account_client().get(reverse("camp_list")).content.decode()
    assert re.search(r'href="/static/css/app\.css\?v=\d+"', html)


def test_footer_on_every_page_without_third_party_images() -> None:
    html = Client().get(reverse("home")).content.decode()
    footer = re.search(r"<footer[^>]*>(.*?)</footer>", html, re.S)
    assert footer is not None
    assert "d-print-none" in re.search(r"<footer[^>]*>", html).group(0)
    assert "<img" not in footer.group(1)
    assert "Buy me a beer" in footer.group(1)
    for link in re.findall(r"<a [^>]*>", footer.group(1)):
        assert 'rel="noopener noreferrer"' in link
    assert "<footer" in account_client().get(reverse("camp_list")).content.decode()
