from django.contrib import admin
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.urls import path, reverse
from django.utils.html import format_html
from .models import SiteSettings, ExchangeRate
from .services import UpbitExchangeService

# Django APScheduler 모델들 import
from django_apscheduler.models import DjangoJob, DjangoJobExecution

# Register your models here.

# 기존 Django APScheduler 어드민 등록 해제
admin.site.unregister(DjangoJob)
admin.site.unregister(DjangoJobExecution)

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

@admin.register(DjangoJob)
class DjangoJobAdmin(admin.ModelAdmin):
    """스케줄 작업 어드민"""
    
    list_display = ('id', 'next_run_time', 'job_state_display')
    list_filter = ('next_run_time', 'job_state')
    readonly_fields = ('id', 'job_state', 'next_run_time')
    
    def job_state_display(self, obj):
        """작업 상태 표시"""
        if obj.job_state == 1:
            return "활성"
        elif obj.job_state == 0:
            return "비활성"
        else:
            return "알 수 없음"
    job_state_display.short_description = '상태'
    
    def has_add_permission(self, request):
        # 스케줄 작업은 자동으로 생성되므로 수동 추가 방지
        return False
    
    def has_change_permission(self, request, obj=None):
        # 스케줄 작업 수정 방지
        return False

@admin.register(DjangoJobExecution)
class DjangoJobExecutionAdmin(admin.ModelAdmin):
    """스케줄 작업 실행 기록 어드민"""
    
    list_display = ('job', 'status_display', 'run_time', 'duration_display', 'finished')
    list_filter = ('status', 'run_time', 'finished')
    readonly_fields = ('job', 'status', 'run_time', 'duration', 'finished', 'exception', 'traceback')
    ordering = ('-run_time',)
    actions = ['cleanup_old_executions']
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('cleanup/', self.admin_site.admin_view(self.cleanup_old_executions_view), name='myshop_djangojobexecution_cleanup'),
        ]
        return custom_urls + urls
    
    def cleanup_old_executions_view(self, request):
        """오래된 실행 기록 정리"""
        try:
            # 최근 5개를 제외하고 모든 기록 삭제
            all_executions = DjangoJobExecution.objects.all().order_by('-run_time')
            if all_executions.count() > 5:
                old_executions = all_executions[5:]
                deleted_count = len(old_executions)
                DjangoJobExecution.objects.filter(
                    id__in=[exec.id for exec in old_executions]
                ).delete()
                messages.success(request, f'{deleted_count}개의 오래된 실행 기록을 삭제했습니다.')
            else:
                messages.info(request, '삭제할 오래된 실행 기록이 없습니다. (최근 5개 유지)')
        except Exception as e:
            messages.error(request, f'실행 기록 정리 중 오류 발생: {str(e)}')
        
        return HttpResponseRedirect(reverse('admin:myshop_djangojobexecution_changelist'))
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['cleanup_url'] = reverse('admin:myshop_djangojobexecution_cleanup')
        return super().changelist_view(request, extra_context=extra_context)
    
    def cleanup_old_executions(self, request, queryset):
        """선택된 실행 기록들을 삭제하는 액션"""
        deleted_count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{deleted_count}개의 실행 기록을 삭제했습니다.')
    
    cleanup_old_executions.short_description = '선택된 실행 기록 삭제'
    
    def status_display(self, obj):
        """실행 상태 표시"""
        status_map = {
            'Started': '시작됨',
            'Executed': '실행됨',
            'Error': '오류',
            'Missed': '누락됨',
        }
        status = status_map.get(obj.status, obj.status)
        
        # 상태에 따른 색상 적용
        if obj.status == 'Executed':
            return format_html('<span style="color: #28a745;">{}</span>', status)
        elif obj.status == 'Error':
            return format_html('<span style="color: #dc3545;">{}</span>', status)
        elif obj.status == 'Started':
            return format_html('<span style="color: #007bff;">{}</span>', status)
        else:
            return format_html('<span style="color: #6c757d;">{}</span>', status)
    
    status_display.short_description = '실행 상태'
    
    def duration_display(self, obj):
        """실행 시간 표시"""
        if obj.duration:
            return f"{obj.duration:.2f}초"
        return "-"
    duration_display.short_description = '실행 시간'
    
    def has_add_permission(self, request):
        # 실행 기록은 자동으로 생성되므로 수동 추가 방지
        return False
    
    def has_change_permission(self, request, obj=None):
        # 실행 기록 수정 방지
        return False

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """사이트 설정 어드민"""
    
    fieldsets = (
        ('기본 설정', {
            'fields': ('site_title', 'site_description', 'admin_site_header'),
            'description': '사이트의 기본 정보를 설정합니다.'
        }),
        ('홈페이지 히어로 섹션', {
            'fields': (
                'hero_title', 
                'hero_subtitle',
                'hero_description',
                ('hero_primary_button_text', 'hero_secondary_button_text')
            ),
            'description': '홈페이지 메인 섹션의 텍스트와 버튼을 설정합니다.'
        }),
        ('유튜브 비디오 설정', {
            'fields': (
                'youtube_video_id', 
                ('youtube_autoplay', 'youtube_mute'),
                ('youtube_loop', 'youtube_controls')
            ),
            'description': '홈페이지에 표시될 유튜브 비디오를 설정합니다. 유튜브 URL에서 v= 뒤의 ID만 입력하세요.'
        }),
        ('환율 API 설정', {
            'fields': ('exchange_rate_update_interval',),
            'description': '업비트 API에서 BTC/KRW 환율을 가져오는 설정입니다.'
        }),
        ('푸터 설정', {
            'fields': (
                'footer_company_name',
                'footer_description', 
                'footer_copyright',
                ('footer_address', 'footer_phone'),
                'footer_business_hours'
            ),
            'description': '사이트 푸터에 표시될 정보를 설정합니다.'
        }),
        ('연락처 및 소셜 미디어', {
            'fields': (
                'contact_email', 
                ('github_url', 'footer_twitter_url'),
                ('footer_telegram_url', 'footer_discord_url')
            ),
            'classes': ('collapse',),
            'description': '연락처 정보와 소셜 미디어 링크를 설정합니다.'
        }),
        ('기능 설정', {
            'fields': ('enable_user_registration', 'enable_store_creation'),
            'classes': ('collapse',),
            'description': '사이트 기능의 활성화/비활성화를 설정합니다.'
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    list_display = ('site_title', 'exchange_rate_update_interval', 'youtube_video_id', 'updated_at')
    
    def has_add_permission(self, request):
        # 설정은 하나만 존재해야 하므로 추가 권한 제한
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # 설정 삭제 방지
        return False
    
    def changelist_view(self, request, extra_context=None):
        # 설정이 없으면 자동으로 생성
        if not SiteSettings.objects.exists():
            SiteSettings.objects.create()
        
        # 설정이 하나만 있으면 바로 편집 페이지로 리다이렉트
        if SiteSettings.objects.count() == 1:
            obj = SiteSettings.objects.first()
            return self.change_view(request, str(obj.pk), extra_context=extra_context)
        
        return super().changelist_view(request, extra_context)
    
    class Media:
        css = {
            'all': ('admin/css/site_settings.css',)
        }
        js = ('admin/js/site_settings.js',)

# Django APScheduler 앱의 verbose_name 변경
from django.apps import apps
try:
    apscheduler_app = apps.get_app_config('django_apscheduler')
    apscheduler_app.verbose_name = '스케줄 작업 관리'
except:
    pass

# Django APScheduler 모델들의 verbose_name 한글화
DjangoJob._meta.verbose_name = '스케줄 작업'
DjangoJob._meta.verbose_name_plural = '스케줄 작업들'
DjangoJobExecution._meta.verbose_name = '작업 실행 기록'
DjangoJobExecution._meta.verbose_name_plural = '작업 실행 기록들'
