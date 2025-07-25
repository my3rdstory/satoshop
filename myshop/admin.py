from django.contrib import admin
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.urls import path, reverse
from django.utils.html import format_html
from .models import SiteSettings, ExchangeRate, DocumentContent, CacheManager
from .services import UpbitExchangeService

# Register your models here.

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """사이트 설정 어드민"""
    
    fieldsets = (
        ('기본 설정', {
            'fields': ('site_title', 'site_description', 'meta_keywords', 'admin_site_header', 'site_logo_url')
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
        ('블링크 API 설정', {
            'fields': ('blink_api_doc_url',),
            'description': '스토어 생성 시 사용자에게 제공되는 블링크 API 관련 문서 링크'
        }),
        ('텔레그램 환율 알림 설정', {
            'fields': ('telegram_bot_token', 'telegram_chat_id', 'enable_telegram_exchange_rate_alerts'),
            'description': '환율 데이터 업데이트 시 텔레그램으로 즉시 알림을 받을 설정입니다.'
        }),
        ('Gmail 도움말 설정', {
            'fields': ('gmail_help_url',),
            'description': '스토어 이메일 설정 시 사용자에게 제공되는 Gmail 앱 비밀번호 설정 도움말 링크'
        }),
        ('밋업 설정', {
            'fields': ('meetup_countdown_seconds',),
            'description': '밋업 신청 과정에서의 제한시간 설정'
        }),
        ('스토어 탐색 페이지 설정', {
            'fields': ('excluded_active_store_ids',),
            'description': '스토어 탐색 페이지에서 특정 스토어들을 제외하는 설정'
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
            # UpbitExchangeService를 사용하여 환율 업데이트
            exchange_rate = UpbitExchangeService.fetch_btc_krw_rate()
            
            if exchange_rate:
                messages.success(
                    request, 
                    f"환율이 성공적으로 업데이트되었습니다. (1 BTC = {exchange_rate.btc_krw_rate:,.0f} KRW)"
                )
            else:
                messages.error(request, "환율 정보를 가져올 수 없습니다. 업비트 API 상태를 확인하세요.")
        
        except Exception as e:
            messages.error(request, f"환율 업데이트 중 오류가 발생했습니다: {str(e)}")
        
        return HttpResponseRedirect(reverse('admin:myshop_exchangerate_changelist'))

    def changelist_view(self, request, extra_context=None):
        """변경 목록에 커스텀 버튼 추가"""
        extra_context = extra_context or {}
        extra_context['update_exchange_rate_url'] = reverse('admin:update_exchange_rate')
        extra_context['site_settings'] = SiteSettings.get_settings()
        return super().changelist_view(request, extra_context)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """변경 페이지에 site_settings 추가"""
        extra_context = extra_context or {}
        extra_context['site_settings'] = SiteSettings.get_settings()
        return super().change_view(request, object_id, form_url, extra_context)
    
    def add_view(self, request, form_url='', extra_context=None):
        """추가 페이지에 site_settings 추가"""
        extra_context = extra_context or {}
        extra_context['site_settings'] = SiteSettings.get_settings()
        return super().add_view(request, form_url, extra_context)


@admin.register(CacheManager)
class CacheManagerAdmin(admin.ModelAdmin):
    """캐시 관리 어드민"""
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        """빈 쿼리셋 반환 (실제 테이블이 없으므로)"""
        return CacheManager.objects.none()
    
    def get_urls(self):
        """커스텀 URL 추가"""
        urls = super().get_urls()
        custom_urls = [
            path('clear-site-settings/', self.admin_site.admin_view(self.clear_site_settings_cache), name='clear_site_settings_cache'),
            path('clear-all-cache/', self.admin_site.admin_view(self.clear_all_cache), name='clear_all_cache'),
        ]
        return custom_urls + urls
    
    def clear_site_settings_cache(self, request):
        """사이트 설정 캐시 클리어"""
        try:
            from django.core.cache import cache
            cache.delete('site_settings_singleton')
            
            messages.success(
                request, 
                "✅ 사이트 설정 캐시가 성공적으로 클리어되었습니다."
            )
        except Exception as e:
            messages.error(request, f"캐시 클리어 중 오류가 발생했습니다: {str(e)}")
        
        return HttpResponseRedirect(reverse('admin:myshop_cachemanager_changelist'))
    
    def clear_all_cache(self, request):
        """전체 캐시 클리어"""
        try:
            from django.core.cache import cache
            cache.clear()
            
            messages.success(
                request, 
                "✅ 전체 캐시가 성공적으로 클리어되었습니다."
            )
        except Exception as e:
            messages.error(request, f"캐시 클리어 중 오류가 발생했습니다: {str(e)}")
        
        return HttpResponseRedirect(reverse('admin:myshop_cachemanager_changelist'))
    
    def changelist_view(self, request, extra_context=None):
        """캐시 관리 페이지"""
        extra_context = extra_context or {}
        extra_context['clear_site_settings_url'] = reverse('admin:clear_site_settings_cache')
        extra_context['clear_all_cache_url'] = reverse('admin:clear_all_cache')
        
        # 캐시 상태 정보 추가
        from django.core.cache import cache
        try:
            # 사이트 설정 캐시 상태 확인
            site_settings_cached = cache.get('site_settings_singleton') is not None
            extra_context['site_settings_cached'] = site_settings_cached
        except:
            extra_context['site_settings_cached'] = False
            
        return super().changelist_view(request, extra_context)


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    """환율 관리 어드민"""
    list_display = ['btc_krw_rate_formatted', 'btc_usd_price_formatted', 'usd_krw_rate_formatted', 'created_at', 'is_recent']
    list_filter = ['created_at']
    search_fields = []
    readonly_fields = ['created_at']
    list_per_page = 10
    
    def btc_krw_rate_formatted(self, obj):
        """환율을 포맷팅하여 표시"""
        return f"{obj.btc_krw_rate:,.0f} KRW"
    btc_krw_rate_formatted.short_description = 'BTC/KRW 환율'
    btc_krw_rate_formatted.admin_order_field = 'btc_krw_rate'
    
    def btc_usd_price_formatted(self, obj):
        """BTC/USD 가격을 포맷팅하여 표시"""
        if obj.btc_usd_price:
            return f"${obj.btc_usd_price:,.2f}"
        return "-"
    btc_usd_price_formatted.short_description = 'BTC/USD 가격'
    btc_usd_price_formatted.admin_order_field = 'btc_usd_price'
    
    def usd_krw_rate_formatted(self, obj):
        """USD/KRW 환율을 포맷팅하여 표시"""
        if obj.usd_krw_rate:
            return f"{obj.usd_krw_rate:,.2f} KRW"
        return "-"
    usd_krw_rate_formatted.short_description = 'USD/KRW 환율'
    usd_krw_rate_formatted.admin_order_field = 'usd_krw_rate'
    
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
    
    def changelist_view(self, request, extra_context=None):
        """변경 목록에 수동 업데이트 버튼 URL 추가"""
        extra_context = extra_context or {}
        extra_context['update_rate_url'] = reverse('admin:update_exchange_rate')
        return super().changelist_view(request, extra_context)
    
    def has_add_permission(self, request):
        # 관리자 페이지에서 직접 추가하지 못하도록 제한
        return False
    
    def has_change_permission(self, request, obj=None):
        # 환율 데이터 수정 방지
        return False


@admin.register(DocumentContent)
class DocumentContentAdmin(admin.ModelAdmin):
    """문서 관리 어드민"""
    
    list_display = ['document_type_display', 'title', 'is_active', 'updated_at']
    list_filter = ['document_type', 'is_active', 'created_at']
    search_fields = ['title', 'content']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 10
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('document_type', 'title', 'is_active'),
            'description': '문서의 기본 정보를 설정합니다.'
        }),
        ('문서 내용', {
            'fields': ('content',),
        }),
        ('메타 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': '문서 생성 및 수정 이력 정보입니다.'
        }),
    )
    
    class Media:
        css = {
            'all': ('admin/css/product_image_modal.css',)
        }
        js = ('admin/js/product_image_modal.js',)
    
    def document_type_display(self, obj):
        """문서 유형을 한글로 표시"""
        type_icons = {
            'terms': '📄',
            'privacy': '🔒',
            'refund': '💰'
        }
        icon = type_icons.get(obj.document_type, '📄')
        return f"{icon} {obj.get_document_type_display()}"
    document_type_display.short_description = '문서 유형'
    document_type_display.admin_order_field = 'document_type'
    
    def get_form(self, request, obj=None, **kwargs):
        """텍스트 영역을 크게 설정하고 마크다운 에디터 스타일 적용"""
        form = super().get_form(request, obj, **kwargs)
        if 'content' in form.base_fields:
            form.base_fields['content'].widget.attrs.update({
                'rows': 25,
                'cols': 120,
                'style': '''
                    width: 100%; 
                    font-family: "Monaco", "Menlo", "Ubuntu Mono", monospace; 
                    font-size: 14px;
                    line-height: 1.5;
                    border: 2px solid #ddd;
                    border-radius: 8px;
                    padding: 15px;
                    background-color: #f8f9fa;
                ''',
                'placeholder': '''# 문서 제목

## 주요 내용

### 세부 사항

여기에 **마크다운** 형식으로 문서 내용을 작성하세요.

- 목록 항목 1
- 목록 항목 2

> 중요한 내용은 인용문으로 작성할 수 있습니다.

**굵은 텍스트**와 *기울임 텍스트*를 사용할 수 있습니다.

[링크 텍스트](https://example.com)

```
코드 블록도 사용 가능합니다
```

| 항목 | 설명 |
|------|------|
| 내용1 | 설명1 |
| 내용2 | 설명2 |'''
            })
        return form
    
    def save_model(self, request, obj, form, change):
        """저장 시 추가 처리"""
        # 기본 제목 설정
        if not obj.title:
            obj.title = obj.get_document_type_display()
        super().save_model(request, obj, form, change)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """변경 페이지에 추가 컨텍스트 제공"""
        extra_context = extra_context or {}
        if object_id:
            try:
                obj = self.get_object(request, object_id)
                if obj:
                    extra_context['document_url'] = f"/document/{obj.document_type}/"
            except:
                pass
        return super().change_view(request, object_id, form_url, extra_context)
