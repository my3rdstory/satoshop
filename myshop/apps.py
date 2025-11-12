from django.apps import AppConfig
from django.contrib import admin


class MyshopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myshop'
    verbose_name = '사이트 설정'
    
    def ready(self):
        # 개발 서버 기본 포트 고정
        self._override_runserver_default_port()

        # 어드민 사이트 설정을 동적으로 로드하되, 실제 데이터베이스 접근은 지연시킴
        self._setup_admin_site_lazy()

    def _override_runserver_default_port(self):
        """runserver 기본 포트를 8011로 강제."""
        try:
            from django.contrib.staticfiles.management.commands.runserver import Command as StaticRunserverCommand
            StaticRunserverCommand.default_port = '8011'
        except ImportError:
            from django.core.management.commands.runserver import Command as CoreRunserverCommand
            CoreRunserverCommand.default_port = '8011'
    
    def _setup_admin_site_lazy(self):
        """어드민 사이트 설정을 지연 로드로 처리"""
        # 런타임에 데이터베이스 접근이 필요할 때만 실행되도록 AdminSite에 동적 속성 추가
        original_index = admin.site.index
        original_each_context = admin.site.each_context
        original_get_app_list = admin.site.get_app_list
        
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

        def prioritized_get_app_list(request):
            """어드민 메뉴에서 주문 관리를 최상단으로 배치"""
            app_list = original_get_app_list(request)
            preferred_order = ['orders']
            prioritized = []
            processed = set()

            for label in preferred_order:
                for app in app_list:
                    if app.get('app_label') == label and app not in prioritized:
                        prioritized.append(app)
                        processed.add(app.get('app_label'))

            for app in app_list:
                if app.get('app_label') not in processed:
                    prioritized.append(app)

            return prioritized

        admin.site.index = dynamic_index
        admin.site.each_context = enhanced_each_context
        admin.site.get_app_list = prioritized_get_app_list
    
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
