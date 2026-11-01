"""The public pages: home, news and docs. No login needed for any of them."""

from pathlib import Path

import markdown
from django.contrib.auth.decorators import login_not_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.safestring import mark_safe

from pages.models import Post

CONTENT_DIR = Path(__file__).parent / "content"
# Also the allow-list: only these files can be opened through the URL.
DOCS = {
    "getting-started": "Getting started",
    "recipes": "Recipes and ingredients",
    "planning": "Planning a camp",
    "shopping-and-budget": "Shopping and budget",
    "bills": "Bills and what you paid",
}


def _render_markdown(text: str) -> str:
    # Only staff (posts) and this repo (docs) write this text, so it's trusted.
    return mark_safe(markdown.markdown(text, extensions=["tables", "sane_lists"]))


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


@login_not_required
def doc(request: HttpRequest, slug: str) -> HttpResponse:
    if slug not in DOCS:
        raise Http404(f"No document {slug}")
    text = (CONTENT_DIR / f"{slug}.md").read_text(encoding="utf-8")
    return render(
        request,
        "pages/doc.html",
        {
            "title": DOCS[slug],
            "body": _render_markdown(text),
            "docs": DOCS.items(),
            "current": slug,
        },
    )
