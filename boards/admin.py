from django.contrib import admin
from .models import Notice, NoticeComment, MemePost, MemeTag


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
    list_display = ['title', 'author', 'created_at', 'views', 'file_size_mb', 'is_active']
    list_filter = ['is_active', 'created_at', 'tags']
    search_fields = ['title', 'author__username', 'tags__name']
    readonly_fields = ['views', 'created_at', 'updated_at', 'image_url', 'thumbnail_url', 
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
            'fields': ('is_active', 'views')
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author').prefetch_related('tags')
    
    def file_size_mb(self, obj):
        return f'{obj.file_size / (1024 * 1024):.2f} MB'
    file_size_mb.short_description = '파일 크기'
