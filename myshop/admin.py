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
            'fields': ('site_title', 'site_description', 'contact_email')
        }),
        ('소셜 미디어', {
            'fields': ('youtube_video_id',),
            'description': '유튜브 비디오 ID만 입력하세요. 예: dQw4w9WgXcQ'
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
    
    def has_add_permission(self, request):
        # 사이트 설정은 하나만 존재해야 하므로 추가 방지
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # 사이트 설정 삭제 방지
        return False

@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    """환율 데이터 어드민"""
    
    list_display = ('btc_krw_rate', 'created_at', 'rate_change_display')
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'api_response_data')
    ordering = ('-created_at',)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('update-rate/', self.admin_site.admin_view(self.update_exchange_rate), name='myshop_exchangerate_update'),
        ]
        return custom_urls + urls
    
    def update_exchange_rate(self, request):
        """수동으로 환율 업데이트"""
        try:
            exchange_rate = UpbitExchangeService.fetch_btc_krw_rate()
            if exchange_rate:
                messages.success(request, f'환율 업데이트 성공: 1 BTC = {exchange_rate.btc_krw_rate:,} KRW')
            else:
                messages.error(request, '환율 업데이트 실패: API에서 데이터를 가져올 수 없습니다.')
        except Exception as e:
            messages.error(request, f'환율 업데이트 중 오류 발생: {str(e)}')
        
        return HttpResponseRedirect(reverse('admin:myshop_exchangerate_changelist'))
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['update_rate_url'] = reverse('admin:myshop_exchangerate_update')
        return super().changelist_view(request, extra_context=extra_context)
    
    def rate_change_display(self, obj):
        """환율 변화 표시"""
        try:
            previous_rate = ExchangeRate.objects.filter(
                created_at__lt=obj.created_at
            ).first()
            
            if previous_rate:
                change = obj.btc_krw_rate - previous_rate.btc_krw_rate
                change_percent = (change / previous_rate.btc_krw_rate) * 100
                
                if change > 0:
                    return format_html(
                        '<span style="color: #28a745;">▲ +{:,.0f} KRW ({:+.2f}%)</span>',
                        change, change_percent
                    )
                elif change < 0:
                    return format_html(
                        '<span style="color: #dc3545;">▼ {:,.0f} KRW ({:+.2f}%)</span>',
                        change, change_percent
                    )
                else:
                    return format_html('<span style="color: #6c757d;">변화 없음</span>')
            return '-'
        except:
            return '-'
    
    rate_change_display.short_description = '변화량'
    
    def has_add_permission(self, request):
        # 환율 데이터는 자동으로 생성되므로 수동 추가 방지
        return False
    
    def has_change_permission(self, request, obj=None):
        # 환율 데이터 수정 방지
        return False
