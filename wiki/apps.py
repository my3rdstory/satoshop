from django.apps import AppConfig


class WikiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "wiki"
    verbose_name = "Wiki"

    def ready(self) -> None:
        # Import signal handlers
        from . import signals  # noqa: F401
