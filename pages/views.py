"""The public pages: home, news and docs. No login needed for any of them."""

from pathlib import Path

import markdown
from django.conf import settings
from django.contrib.auth.decorators import login_not_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.safestring import mark_safe
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from pages.models import Post

CONTENT_DIR = Path(__file__).parent / "content"
# Also the allow-list: only these files can be opened through the URL.
DOCS = {
    "getting-started": _("Getting started"),
    "recipes": _("Recipes and ingredients"),
    "planning": _("Planning a camp"),
    "shopping-and-budget": _("Shopping and budget"),
    "bills": _("Bills and what you paid"),
}


def _render_markdown(text: str) -> str:
    # Only staff (posts) and this repo (docs) write this text, so it's trusted.
    return mark_safe(markdown.markdown(text, extensions=["tables", "sane_lists"]))


def split_title(text: str) -> tuple[str | None, str]:
    """A help file's `# Title` first line, and the text after it; (None, text)
    when the first line that isn't blank isn't a `# ` heading."""
    stripped = text.lstrip("\n")
    first, _newline, rest = stripped.partition("\n")
    if first.startswith("# "):
        return first[2:].strip(), rest
    return None, text


@login_not_required
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "pages/home.html", {"posts": Post.objects.published()[:3]})


@login_not_required
def post_list(request: HttpRequest) -> HttpResponse:
    return render(request, "pages/post_list.html", {"posts": Post.objects.published()})


@login_not_required
def post_detail(request: HttpRequest, slug: str) -> HttpResponse:
    post = get_object_or_404(Post.objects.published(), slug=slug)
    return render(
        request,
        "pages/post_detail.html",
        {"post": post, "body": _render_markdown(post.body)},
    )


def doc_path(slug: str, language: str | None) -> Path | None:
    """The help file for a slug, or None when it isn't in DOCS. The path is built
    from the allow-listed names only, never from the URL or the language cookie.
    English is the source; a translation sits next to it as <slug>.<language>.md."""
    name = next((name for name in DOCS if name == slug), None)
    if name is None:
        return None
    code = next((code for code, _label in settings.LANGUAGES if code == language), None)
    translated = CONTENT_DIR / f"{name}.{code}.md"
    if code and translated.exists():
        return translated
    return CONTENT_DIR / f"{name}.md"


@login_not_required
def doc(request: HttpRequest, slug: str) -> HttpResponse:
    path = doc_path(slug, get_language())
    if path is None:
        raise Http404("No such document")
    title, text = split_title(path.read_text(encoding="utf-8"))
    return render(
        request,
        "pages/doc.html",
        {
            "title": title or DOCS[slug],
            "body": _render_markdown(text),
            "docs": DOCS.items(),
            "current": slug,
        },
    )
