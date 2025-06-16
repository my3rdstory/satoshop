from django.apps import AppConfig


class StoresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stores'
    verbose_name = '2. 스토어 관리'
    
    def ready(self):
        """앱이 준비되면 시그널을 등록합니다."""
        import stores.signals