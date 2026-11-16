from django.contrib import admin

from pages.models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "is_published", "published_at"]
    prepopulated_fields = {"slug": ["title"]}
