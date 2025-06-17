from django.apps import AppConfig
from django.contrib import admin


class MyshopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myshop'
    verbose_name = '사이트 설정'
    
    def ready(self):
        # 어드민 사이트 설정을 동적으로 로드하되, 실제 데이터베이스 접근은 지연시킴
        self._setup_admin_site_lazy()
    
    def _setup_admin_site_lazy(self):
        """어드민 사이트 설정을 지연 로드로 처리"""
        # 런타임에 데이터베이스 접근이 필요할 때만 실행되도록 AdminSite에 동적 속성 추가
        original_index = admin.site.index
        
        def dynamic_index(request, extra_context=None):
            # 첫 번째 관리자 페이지 접근 시에만 설정 로드
            if not hasattr(admin.site, '_satoshop_configured'):
                self._apply_admin_settings()
                admin.site._satoshop_configured = True
            return original_index(request, extra_context)
        
        admin.site.index = dynamic_index
    
    def _apply_admin_settings(self):
        """실제 어드민 사이트 설정을 SiteSettings에서 가져와서 적용"""
        try:
            from django.db import connection
            # 데이터베이스 연결 상태 확인
            if connection.connection is None:
                connection.ensure_connection()
            
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
