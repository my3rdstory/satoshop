from django.contrib import admin
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.urls import path, reverse
from django.utils.html import format_html
from .models import SiteSettings, ExchangeRate
from .services import UpbitExchangeService

# Register your models here.

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """사이트 설정 어드민"""
    
    fieldsets = (
        ('기본 설정', {
            'fields': ('site_title', 'site_description', 'meta_keywords', 'admin_site_header')
        }),
        ('홈페이지 히어로 섹션', {
            'fields': (
                'hero_title', 
                'hero_subtitle', 
                'hero_description',
                'hero_primary_button_text',
                'hero_secondary_button_text'
            ),
            'description': '홈페이지 메인 섹션의 텍스트를 설정합니다.'
        }),
        ('유튜브 비디오 설정', {
            'fields': (
                'youtube_video_id',
                'youtube_autoplay',
                'youtube_mute', 
                'youtube_loop',
                'youtube_controls'
            ),
            'description': '홈페이지 배경 비디오 설정. 유튜브 비디오 ID만 입력하세요. 예: dd2RzyPu4ok'
        }),
        ('연락처 정보', {
            'fields': ('contact_email', 'github_url')
        }),
        ('푸터 설정', {
            'fields': (
                'footer_company_name',
                'footer_description', 
                'footer_copyright',
                'footer_address',
                'footer_phone',
                'footer_business_hours'
            ),
            'description': '웹사이트 하단 푸터 영역의 정보를 설정합니다.'
        }),
        ('소셜 미디어 링크', {
            'fields': (
                'footer_twitter_url',
                'footer_telegram_url', 
                'footer_discord_url'
            ),
            'description': '푸터에 표시될 소셜 미디어 링크들을 설정합니다.'
        }),
        ('기능 설정', {
            'fields': (
                'enable_user_registration',
                'enable_store_creation'
            ),
            'description': '사이트의 주요 기능들을 활성화/비활성화합니다.'
        }),
        ('SEO 및 분석', {
            'fields': (
                'google_analytics_id',
                'og_default_image',
                'og_site_name',
                'favicon_url'
            ),
            'description': 'Google Analytics, Open Graph 메타태그 및 파비콘 설정'
        }),
        ('환율 설정', {
            'fields': ('exchange_rate_update_interval',),
            'description': 'GitHub Actions에서 환율을 자동 업데이트하는 간격을 설정합니다.'
        }),
        ('고급 설정', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 10
    
    def has_add_permission(self, request):
        # 사이트 설정은 하나만 존재해야 하므로 추가 방지
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # 사이트 설정 삭제 방지
        return False

    def get_urls(self):
        """커스텀 URL 추가"""
        urls = super().get_urls()
        custom_urls = [
            path('update-exchange-rate/', self.admin_site.admin_view(self.update_exchange_rate), name='update_exchange_rate'),
        ]
        return custom_urls + urls

    def update_exchange_rate(self, request):
        """환율 업데이트 액션"""
        try:
            service = UpbitExchangeService()
            rate_info = service.get_current_rate()
            
            if rate_info:
                rate, created = ExchangeRate.objects.get_or_create(
                    currency='KRW',
                    defaults={'rate': rate_info['rate']}
                )
                if not created:
                    rate.rate = rate_info['rate']
                    rate.save()
                
                messages.success(request, f"환율이 성공적으로 업데이트되었습니다. (1 USD = {rate_info['rate']:,.2f} KRW)")
            else:
                messages.error(request, "환율 정보를 가져올 수 없습니다.")
        
        except Exception as e:
            messages.error(request, f"환율 업데이트 중 오류가 발생했습니다: {str(e)}")
        
        return HttpResponseRedirect(reverse('admin:myshop_sitesettings_changelist'))

    def changelist_view(self, request, extra_context=None):
        """변경 목록에 커스텀 버튼 추가"""
        extra_context = extra_context or {}
        extra_context['update_exchange_rate_url'] = reverse('admin:update_exchange_rate')
        return super().changelist_view(request, extra_context)


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    """환율 관리 어드민"""
    list_display = ['btc_krw_rate_formatted', 'created_at', 'is_recent']
    list_filter = ['created_at']
    search_fields = []
    readonly_fields = ['created_at']
    list_per_page = 10
    
    def btc_krw_rate_formatted(self, obj):
        """환율을 포맷팅하여 표시"""
        return f"{obj.btc_krw_rate:,.0f} KRW"
    btc_krw_rate_formatted.short_description = 'BTC/KRW 환율'
    btc_krw_rate_formatted.admin_order_field = 'btc_krw_rate'
    
    def is_recent(self, obj):
        """최근 업데이트 여부 표시"""
        from django.utils import timezone
        from datetime import timedelta
        
        if timezone.now() - obj.created_at < timedelta(hours=1):
            return format_html('<span style="color: green;">최신</span>')
        elif timezone.now() - obj.created_at < timedelta(hours=24):
            return format_html('<span style="color: orange;">1일 이내</span>')
        else:
            return format_html('<span style="color: red;">오래됨</span>')
    is_recent.short_description = '상태'
    
    def has_add_permission(self, request):
        # 관리자 페이지에서 직접 추가하지 못하도록 제한
        return False
    
    def has_change_permission(self, request, obj=None):
        # 환율 데이터 수정 방지
        return False
