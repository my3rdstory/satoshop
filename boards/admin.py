from django.contrib import admin
from django.db.models import F
from django.contrib.auth.models import User
from .models import Notice, NoticeComment, MemePost, MemeTag, HallOfFame


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
    list_display = ['user_display', 'title', 'created_at', 'views', 'order', 'is_active', 'created_by']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 
                     'title', 'description', 'created_by__username']
    readonly_fields = ['views', 'created_at', 'updated_at', 'image_url', 'thumbnail_url', 
                      'file_size', 'width', 'height', 'file_size_mb']
    list_editable = ['order', 'is_active']
    ordering = ['order', '-created_at']
    list_per_page = 20
    autocomplete_fields = ['user']
    raw_id_fields = ['created_by']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'title', 'description', 'order')
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
        return super().get_queryset(request).select_related('user', 'created_by')
    
    def user_display(self, obj):
        """사용자 표시 (username과 실명 함께 표시)"""
        full_name = obj.user.get_full_name()
        if full_name:
            return f"{obj.user.username} ({full_name})"
        return obj.user.username
    user_display.short_description = '사용자'
    user_display.admin_order_field = 'user__username'
    
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


# User 모델에 자동완성 기능 추가를 위한 Admin 설정
class UserAdmin(admin.ModelAdmin):
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
# User 모델이 이미 등록되어 있다면 먼저 해제
if admin.site.is_registered(User):
    admin.site.unregister(User)
    
# User 모델 다시 등록 (자동완성 지원)
admin.site.register(User, UserAdmin)
