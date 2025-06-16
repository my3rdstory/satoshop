from django.apps import AppConfig
from django.contrib import admin


class MyshopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myshop'
    verbose_name = '1. 사이트 설정'
    
    def ready(self):
        # 어드민 사이트 설정을 동적으로 로드
        self.setup_admin_site()
    
    def setup_admin_site(self):
        """어드민 사이트 설정을 SiteSettings에서 가져와서 적용"""
        try:
            from .models import SiteSettings
            settings = SiteSettings.get_settings()
            admin.site.site_header = settings.admin_site_header
            admin.site.site_title = f"{settings.site_title} Admin"
            admin.site.index_title = '사이트 관리 대시보드'
        except Exception:
            # 마이그레이션 전이나 오류 상황에서는 기본값 사용
            admin.site.site_header = "SatoShop 관리자"
            admin.site.site_title = "SatoShop Admin"
            admin.site.index_title = '사이트 관리 대시보드'
