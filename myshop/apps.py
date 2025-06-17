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
        original_each_context = admin.site.each_context
        
        def dynamic_index(request, extra_context=None):
            # 매번 설정 로드 (설정 변경 반영을 위해)
            self._apply_admin_settings()
            
            # site_settings를 컨텍스트에 추가
            if extra_context is None:
                extra_context = {}
            
            try:
                from .models import SiteSettings
                extra_context['site_settings'] = SiteSettings.get_settings()
            except Exception:
                extra_context['site_settings'] = None
                
            return original_index(request, extra_context)
        
        def enhanced_each_context(request):
            """모든 admin 페이지에 site_settings 추가 및 설정 업데이트"""
            # 매번 설정 로드
            self._apply_admin_settings()
            
            context = original_each_context(request)
            try:
                from .models import SiteSettings
                context['site_settings'] = SiteSettings.get_settings()
            except Exception:
                context['site_settings'] = None
            return context
        
        admin.site.index = dynamic_index
        admin.site.each_context = enhanced_each_context
    
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
