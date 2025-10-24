from __future__ import annotations

from django.contrib import admin

from .models import WikiEmbedding, WikiEntry


@admin.register(WikiEntry)
class WikiEntryAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "updated_at", "created_by", "updated_by")
    list_filter = ("is_published", "created_at", "updated_at")
    search_fields = ("title", "content", "tags")
    readonly_fields = ("created_at", "updated_at")


@admin.register(WikiEmbedding)
class WikiEmbeddingAdmin(admin.ModelAdmin):
    list_display = ("entry", "provider", "embedding_model", "updated_at")
    list_filter = ("provider", "embedding_model", "created_at")
    search_fields = ("entry__title",)
    readonly_fields = ("entry", "embedding", "content_snapshot", "created_at", "updated_at")
