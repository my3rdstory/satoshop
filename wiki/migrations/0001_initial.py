from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.contrib.postgres.fields
from django.core.validators import MaxLengthValidator
import pgvector.django


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        pgvector.django.VectorExtension(),
        migrations.CreateModel(
            name="WikiEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=100)),
                (
                    "content",
                    models.TextField(validators=[MaxLengthValidator(1000)]),
                ),
                (
                    "tags",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=50),
                        blank=True,
                        default=list,
                        help_text="Comma separated keywords used for retrieval.",
                        size=None,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_published", models.BooleanField(default=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="wiki_entries_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="wiki_entries_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at"],
                "permissions": [("manage_wiki", "Can create and edit wiki entries")],
            },
        ),
        migrations.CreateModel(
            name="WikiEmbedding",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("embedding", pgvector.django.VectorField(dimensions=1536)),
                ("embedding_model", models.CharField(max_length=100)),
                ("provider", models.CharField(max_length=50)),
                ("content_snapshot", models.TextField(help_text="Content snapshot used while generating this embedding.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "entry",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="embedding",
                        to="wiki.wikientry",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="wikiembedding",
            index=pgvector.django.HnswIndex(
                fields=["embedding"],
                name="wiki_embedding_hnsw",
                m=16,
                ef_construction=64,
            ),
        ),
    ]
