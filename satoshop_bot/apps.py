from django.apps import AppConfig


class SatoshopBotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'satoshop_bot'
    verbose_name = '봇 연동'

    def ready(self) -> None:
        from . import signals  # noqa: F401
