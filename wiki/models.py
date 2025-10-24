from __future__ import annotations

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxLengthValidator
from django.db import models
from pgvector.django import HnswIndex, VectorField


class WikiEntry(models.Model):
    """
    Core wiki content entity managed through the backoffice.
    """

    title = models.CharField(max_length=100)
    content = models.TextField(validators=[MaxLengthValidator(1000)])
    tags = ArrayField(
        base_field=models.CharField(max_length=50),
        blank=True,
        default=list,
        help_text="Comma separated keywords used for retrieval.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wiki_entries_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wiki_entries_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-updated_at"]
        permissions = [
            ("manage_wiki", "Can create and edit wiki entries"),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def tags_display(self) -> str:
        return ", ".join(self.tags)


class WikiEmbedding(models.Model):
    """
    Vector representation of wiki entries, stored in PostgreSQL via pgvector.
    """

    entry = models.OneToOneField(
        WikiEntry,
        on_delete=models.CASCADE,
        related_name="embedding",
    )
    embedding = VectorField(dimensions=1536)
    embedding_model = models.CharField(max_length=100)
    provider = models.CharField(max_length=50)
    content_snapshot = models.TextField(
        help_text="Content snapshot used while generating this embedding."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            HnswIndex(
                name="wiki_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
            )
        ]

    def __str__(self) -> str:
        return f"Embedding<{self.entry_id}>"
