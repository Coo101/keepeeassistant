"""News posts on the public site (SPEC §9.9)."""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class PostQuerySet(models.QuerySet):
    def published(self) -> "PostQuerySet":
        return self.filter(is_published=True, published_at__lte=timezone.now())


class Post(models.Model):
    title = models.CharField(max_length=200, verbose_name=_("title"))
    slug = models.SlugField(unique=True)
    body = models.TextField(verbose_name=_("text"), help_text=_("Written in Markdown"))
    is_published = models.BooleanField(default=True, verbose_name=_("published"))
    published_at = models.DateTimeField(
        default=timezone.now, verbose_name=_("publication date")
    )

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at"]

    def __str__(self) -> str:
        return self.title
