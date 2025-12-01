from django.contrib import admin
from django.db.models import F
from django.contrib.auth.models import User
from accounts.admin import CustomUserAdmin
from .models import Notice, NoticeComment, MemePost, MemeTag, HallOfFame, HallOfFamePermission


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'created_at', 'views', 'is_pinned', 'is_active']
    list_filter = ['is_pinned', 'is_active', 'created_at']
    search_fields = ['title', 'content', 'author__username']
    readonly_fields = ['views', 'created_at', 'updated_at']
    list_editable = ['is_pinned', 'is_active']
    ordering = ['-is_pinned', '-created_at']
    list_per_page = 10
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('title', 'content', 'author')
        }),
        ('설정', {
            'fields': ('is_pinned', 'is_active')
        }),
        ('통계', {
            'fields': ('views', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author')
    
    def save_model(self, request, obj, form, change):
        if not change:  # 새 게시글인 경우
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(NoticeComment)
class NoticeCommentAdmin(admin.ModelAdmin):
    list_display = ['notice', 'author', 'content_preview', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['content', 'author__username', 'notice__title']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_active']
    ordering = ['-created_at']
    list_per_page = 10
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author', 'notice')
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '댓글 미리보기'


@admin.register(MemeTag)
class MemeTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'meme_count']
    search_fields = ['name']
    ordering = ['name']
    
    def meme_count(self, obj):
        return obj.memes.filter(is_active=True).count()
    meme_count.short_description = '사용 횟수'


@admin.register(MemePost)
class MemePostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'created_at', 'views', 'list_copy_count', 
                    'list_view_count', 'detail_copy_count', 'total_clicks', 'file_size_mb', 'is_active']
    list_filter = ['is_active', 'created_at', 'tags']
    search_fields = ['title', 'author__username', 'tags__name']
    readonly_fields = ['views', 'list_copy_count', 'list_view_count', 'detail_copy_count',
                      'created_at', 'updated_at', 'image_url', 'thumbnail_url', 
                      'file_size', 'width', 'height']
    list_editable = ['is_active']
    ordering = ['-created_at']
    list_per_page = 20
    filter_horizontal = ['tags']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('title', 'author', 'tags')
        }),
        ('이미지 정보', {
            'fields': ('image_url', 'thumbnail_url', 'original_filename', 
                      'file_size', 'width', 'height'),
            'classes': ('collapse',)
        }),
        ('저장 경로', {
            'fields': ('image_path', 'thumbnail_path'),
            'classes': ('collapse',)
        }),
        ('상태', {
            'fields': ('is_active',)
        }),
        ('통계', {
            'fields': ('views', 'list_copy_count', 'list_view_count', 'detail_copy_count')
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author').prefetch_related('tags').annotate(
            total_clicks_db=F('list_copy_count') + F('list_view_count') + F('detail_copy_count')
        )
    
    def file_size_mb(self, obj):
        return f'{obj.file_size / (1024 * 1024):.2f} MB'
    file_size_mb.short_description = '파일 크기'
    
    def total_clicks(self, obj):
        """전체 클릭 수 (목록 복사 + 목록 보기 + 상세 복사)"""
        return getattr(obj, 'total_clicks_db', obj.list_copy_count + obj.list_view_count + obj.detail_copy_count)
    total_clicks.short_description = '총 클릭수'
    total_clicks.admin_order_field = 'total_clicks_db'


@admin.register(HallOfFame)
class HallOfFameAdmin(admin.ModelAdmin):
    list_display = ['year_month_display', 'created_at', 'views', 'is_active', 'created_by']
    list_filter = ['is_active', 'year', 'month', 'created_at']
    search_fields = ['year', 'month', 'created_by__username']
    readonly_fields = ['views', 'created_at', 'updated_at', 'image_url', 'thumbnail_url', 
                      'file_size', 'width', 'height', 'file_size_mb']
    list_editable = ['is_active']
    ordering = ['-created_at']
    list_per_page = 20
    raw_id_fields = ['created_by']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('year', 'month')
        }),
        ('이미지 정보', {
            'fields': ('image_url', 'thumbnail_url', 'original_filename', 
                      'file_size_mb', 'width', 'height'),
            'classes': ('collapse',)
        }),
        ('저장 경로', {
            'fields': ('image_path', 'thumbnail_path'),
            'classes': ('collapse',)
        }),
        ('상태', {
            'fields': ('is_active',)
        }),
        ('통계', {
            'fields': ('views',)
        }),
        ('관리 정보', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')
    
    def year_month_display(self, obj):
        """년월 표시"""
        return f"{obj.year}년 {obj.month}월"
    year_month_display.short_description = '년월'
    year_month_display.admin_order_field = 'year'
    
    def file_size_mb(self, obj):
        """파일 크기를 MB 단위로 표시"""
        if obj.file_size:
            return f'{obj.file_size / (1024 * 1024):.2f} MB'
        return '0 MB'
    file_size_mb.short_description = '파일 크기'
    
    def save_model(self, request, obj, form, change):
        if not change:  # 새로 생성하는 경우
            if not obj.created_by:
                obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    class Media:
        css = {
            'all': ('admin/css/autocomplete.css',)
        }
        js = ('admin/js/autocomplete.js',)


@admin.register(HallOfFamePermission)
class HallOfFamePermissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'can_upload', 'created_at', 'created_by']
    list_filter = ['can_upload', 'created_at']
    search_fields = ['user__username', 'user__email', 'created_by__username']
    list_editable = ['can_upload']
    ordering = ['-created_at']
    autocomplete_fields = ['user']
    raw_id_fields = ['created_by']
    
    fieldsets = (
        ('권한 정보', {
            'fields': ('user', 'can_upload')
        }),
        ('관리 정보', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at']
    
    def save_model(self, request, obj, form, change):
        if not change:  # 새로 생성하는 경우
            if not obj.created_by:
                obj.created_by = request.user
        super().save_model(request, obj, form, change)


# User 모델 자동완성/검색 설정 + accounts 확장 인라인 포함
class UserAdmin(CustomUserAdmin):
    search_fields = CustomUserAdmin.search_fields

# User 모델이 이미 등록되어 있다면 먼저 해제 후 재등록
if admin.site.is_registered(User):
    admin.site.unregister(User)
admin.site.register(User, UserAdmin)
