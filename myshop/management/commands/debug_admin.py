from django.core.management.base import BaseCommand
from django.contrib import admin
from django.apps import apps


class Command(BaseCommand):
    help = 'Django 어드민에 등록된 모델들을 확인합니다 (배포 디버깅용)'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔍 Django 어드민 모델 등록 상태 확인')
        )
        
        # 전체 등록된 모델 수
        total_models = len(admin.site._registry)
        self.stdout.write(f'📊 총 등록된 모델 수: {total_models}개')
        
        # myshop 모델들 확인
        self.stdout.write('\n💰 myshop 모델 상태 확인:')
        
        try:
            from myshop.models import ExchangeRate, SiteSettings
            
            if ExchangeRate in admin.site._registry:
                self.stdout.write('✅ ExchangeRate 어드민 등록됨')
                rate_count = ExchangeRate.objects.count()
                self.stdout.write(f'📊 환율 데이터 수: {rate_count}개')
                
                # 최신 환율 정보
                latest_rate = ExchangeRate.objects.first()
                if latest_rate:
                    self.stdout.write(f'💰 최신 환율: 1 BTC = {latest_rate.btc_krw_rate:,} KRW')
                    self.stdout.write(f'🕐 마지막 업데이트: {latest_rate.created_at}')
            else:
                self.stdout.write('❌ ExchangeRate 어드민 미등록')
                
            if SiteSettings in admin.site._registry:
                self.stdout.write('✅ SiteSettings 어드민 등록됨')
                settings = SiteSettings.get_settings()
                self.stdout.write(f'🏠 사이트 제목: {settings.site_title}')
                self.stdout.write(f'👥 회원가입 허용: {"✅" if settings.enable_user_registration else "❌"}')
                self.stdout.write(f'🏪 스토어 생성 허용: {"✅" if settings.enable_store_creation else "❌"}')
            else:
                self.stdout.write('❌ SiteSettings 어드민 미등록')
                
        except Exception as e:
            self.stdout.write(f'❌ myshop 모델 확인 실패: {e}')
        
        # 등록된 모든 모델 목록
        self.stdout.write('\n📋 등록된 모든 어드민 모델:')
        for model, admin_class in admin.site._registry.items():
            app_label = model._meta.app_label
            model_name = model._meta.model_name
            self.stdout.write(f'  - {app_label}.{model_name}')
        
        self.stdout.write(
            self.style.SUCCESS('\n✅ 어드민 상태 확인 완료')
        ) 