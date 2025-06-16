from django.core.management.base import BaseCommand
from django.contrib import admin
from django.apps import apps


class Command(BaseCommand):
    help = 'Django 어드민에 등록된 모델들을 확인합니다 (Render.com 디버깅용)'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔍 Django 어드민 모델 등록 상태 확인')
        )
        
        # 전체 등록된 모델 수
        total_models = len(admin.site._registry)
        self.stdout.write(f'📊 총 등록된 모델 수: {total_models}개')
        
        # Django APScheduler 관련 확인
        self.stdout.write('\n🔧 Django APScheduler 상태 확인:')
        
        try:
            from django_apscheduler.models import DjangoJob, DjangoJobExecution
            self.stdout.write('✅ Django APScheduler 모델 import 성공')
            
            # 어드민 등록 확인
            if DjangoJob in admin.site._registry:
                self.stdout.write('✅ DjangoJob 어드민 등록됨')
            else:
                self.stdout.write('❌ DjangoJob 어드민 미등록')
                
            if DjangoJobExecution in admin.site._registry:
                self.stdout.write('✅ DjangoJobExecution 어드민 등록됨')
            else:
                self.stdout.write('❌ DjangoJobExecution 어드민 미등록')
                
            # 데이터베이스 테이블 확인
            job_count = DjangoJob.objects.count()
            execution_count = DjangoJobExecution.objects.count()
            self.stdout.write(f'📊 DB 작업 수: {job_count}개')
            self.stdout.write(f'📊 DB 실행 기록 수: {execution_count}개')
            
        except ImportError as e:
            self.stdout.write(f'❌ Django APScheduler import 실패: {e}')
        except Exception as e:
            self.stdout.write(f'❌ Django APScheduler 확인 실패: {e}')
        
        # myshop 모델들 확인
        self.stdout.write('\n💰 myshop 모델 상태 확인:')
        
        try:
            from myshop.models import ExchangeRate, SiteSettings
            
            if ExchangeRate in admin.site._registry:
                self.stdout.write('✅ ExchangeRate 어드민 등록됨')
                rate_count = ExchangeRate.objects.count()
                self.stdout.write(f'📊 환율 데이터 수: {rate_count}개')
            else:
                self.stdout.write('❌ ExchangeRate 어드민 미등록')
                
            if SiteSettings in admin.site._registry:
                self.stdout.write('✅ SiteSettings 어드민 등록됨')
            else:
                self.stdout.write('❌ SiteSettings 어드민 미등록')
                
        except Exception as e:
            self.stdout.write(f'❌ myshop 모델 확인 실패: {e}')
        
        # 환경 변수 확인
        self.stdout.write('\n🌍 환경 변수 확인:')
        import os
        scheduler_enabled = os.environ.get('ENABLE_DJANGO_SCHEDULER', 'false')
        self.stdout.write(f'📋 ENABLE_DJANGO_SCHEDULER: {scheduler_enabled}')
        
        # 등록된 모든 모델 목록
        self.stdout.write('\n📋 등록된 모든 어드민 모델:')
        for model, admin_class in admin.site._registry.items():
            app_label = model._meta.app_label
            model_name = model._meta.model_name
            self.stdout.write(f'  - {app_label}.{model_name}')
        
        self.stdout.write(
            self.style.SUCCESS('\n✅ 어드민 상태 확인 완료')
        ) 