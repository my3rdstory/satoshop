from django.apps import AppConfig
from django.contrib import admin


class MyshopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myshop'
    verbose_name = '1. 사이트 설정'
    
    def ready(self):
        # Render.com Cron Jobs를 사용하므로 Django 앱 내부 스케줄러는 비활성화
        # 로컬 개발 환경에서만 스케줄러 사용 (선택적)
        import os
        import sys
        
        # 마이그레이션, collectstatic 등의 명령어 실행 시에는 스케줄러 시작하지 않음
        if any(cmd in sys.argv for cmd in ['migrate', 'makemigrations', 'collectstatic', 'createsuperuser', 'shell']):
            return
        
        # 환경 변수로 스케줄러 활성화 여부 제어 (기본값: 비활성화)
        enable_scheduler = os.environ.get('ENABLE_DJANGO_SCHEDULER', 'false').lower() == 'true'
        
        if enable_scheduler:
            # runserver 명령어로 실행될 때 또는 메인 프로세스에서 스케줄러 시작
            # RUN_MAIN 환경변수는 Django 개발 서버의 메인 프로세스를 나타냄
            if 'runserver' in sys.argv:
                # 개발 서버의 경우 RUN_MAIN이 설정된 메인 프로세스에서만 실행
                if os.environ.get('RUN_MAIN') == 'true':
                    try:
                        from . import scheduler
                        scheduler.start_scheduler()
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"스케줄러 시작 실패: {e}")
            elif 'runserver' not in sys.argv and not any(cmd in sys.argv for cmd in ['test', 'check']):
                # 프로덕션 환경 (gunicorn 등)에서는 바로 시작
                try:
                    from . import scheduler
                    scheduler.start_scheduler()
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"스케줄러 시작 실패: {e}")
        else:
            # 스케줄러 비활성화 상태 로그
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Django 내부 스케줄러가 비활성화되었습니다. Render.com Cron Jobs를 사용하세요.")
        
        # Django APScheduler 앱의 verbose_name 한글화
        try:
            from django.apps import apps
            apscheduler_app = apps.get_app_config('django_apscheduler')
            apscheduler_app.verbose_name = '스케줄 작업 관리'
        except Exception:
            pass  # 앱이 없으면 무시

        # 순환 import 방지를 위해 여기서 import
        try:
            from .models import SiteSettings
            
            # 사이트 설정에서 admin 사이트 헤더 업데이트
            try:
                site_settings = SiteSettings.get_settings()
                if site_settings and site_settings.admin_site_header:
                    admin.site.site_header = site_settings.admin_site_header
                    admin.site.site_title = f"{site_settings.site_title} Admin"
                    admin.site.index_title = '사이트 관리 대시보드'
            except Exception:
                # 마이그레이션 전이나 DB 오류 시에는 기본값 사용
                pass
        except ImportError:
            # 앱이 완전히 로드되지 않은 경우
            pass
