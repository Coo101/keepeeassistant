"""News posts on the public site (SPEC §9.9)."""

from django.db import models
from django.utils import timezone


class PostQuerySet(models.QuerySet):
    def published(self) -> "PostQuerySet":
        return self.filter(is_published=True, published_at__lte=timezone.now())


class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    body = models.TextField(help_text="Written in Markdown")
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now)

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at"]

    def __str__(self) -> str:
        return self.title
