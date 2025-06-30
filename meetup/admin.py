from django.contrib import admin
from django.utils.html import format_html
from .models import Meetup, MeetupImage, MeetupOption, MeetupChoice

class MeetupImageInline(admin.TabularInline):
    """밋업 이미지 인라인 어드민"""
    model = MeetupImage
    extra = 0  # 빈 폼 0개
    readonly_fields = ('view_image_button', 'file_size_display', 'uploaded_at', 'uploaded_by')
    fields = ('view_image_button', 'original_name', 'file_size_display', 'width', 'height', 'order', 'uploaded_at', 'uploaded_by')
    ordering = ('order', 'uploaded_at')
    
    def view_image_button(self, obj):
        """이미지 보기 버튼 (모달 방식) - 아이콘만 표시"""
        if obj and obj.file_url:
            return format_html(
                '<button type="button" class="button" onclick="showImageModal(\'{}\', \'{}\')" style="background-color: #007cba; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;" title="이미지 보기">'
                '<i class="fas fa-eye"></i>'
                '</button>',
                obj.file_url,
                obj.original_name
            )
        return "이미지 없음"
    view_image_button.short_description = '이미지'
    
    def file_size_display(self, obj):
        """파일 크기 표시"""
        if obj:
            return obj.get_file_size_display()
        return ""
    file_size_display.short_description = '파일 크기'

class MeetupChoiceInline(admin.TabularInline):
    """밋업 선택지 인라인 어드민"""
    model = MeetupChoice
    extra = 1
    readonly_fields = ['created_at']
    fields = ('name', 'additional_price', 'order', 'created_at')

class MeetupOptionInline(admin.TabularInline):
    """밋업 옵션 인라인 어드민"""
    model = MeetupOption
    extra = 1
    readonly_fields = ['created_at']
    fields = ('name', 'is_required', 'order', 'created_at')

@admin.register(Meetup)
class MeetupAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'price_display', 'is_active', 'is_discounted', 'max_participants', 'remaining_spots_display', 'created_at']
    list_filter = ['store', 'is_active', 'is_discounted', 'is_temporarily_closed', 'created_at']
    search_fields = ['name', 'description', 'store__store_name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'current_price', 'is_early_bird_active', 'public_discount_rate']
    inlines = [MeetupImageInline, MeetupOptionInline]
    
    def price_display(self, obj):
        """가격 표시"""
        if obj.is_discounted and obj.discounted_price:
            return format_html(
                '<span style="text-decoration: line-through; color: #999;">{} sats</span><br>'
                '<span style="color: #e74c3c; font-weight: bold;">{} sats</span>',
                f"{obj.price:,}",
                f"{obj.discounted_price:,}"
            )
        return f"{obj.price:,} sats"
    price_display.short_description = '참가비'
    
    def remaining_spots_display(self, obj):
        """남은 자리 표시"""
        if obj.max_participants:
            remaining = obj.remaining_spots
            if remaining is not None:
                if remaining == 0:
                    return format_html('<span style="color: #e74c3c;">마감</span>')
                elif remaining <= 5:
                    return format_html('<span style="color: #f39c12;">{} 자리</span>', str(remaining))
                else:
                    return format_html('<span style="color: #27ae60;">{} 자리</span>', str(remaining))
        return '무제한'
    remaining_spots_display.short_description = '남은 자리'
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('store', 'name', 'description')
        }),
        ('가격 정보', {
            'fields': ('price', 'is_discounted', 'discounted_price', 'early_bird_end_date', 'early_bird_end_time', 'current_price', 'public_discount_rate')
        }),
        ('참가자 관리', {
            'fields': ('max_participants', 'completion_message')
        }),
        ('상태 정보', {
            'fields': ('is_active', 'is_temporarily_closed', 'is_early_bird_active')
        }),
        ('메타 정보', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(MeetupImage)
class MeetupImageAdmin(admin.ModelAdmin):
    """밋업 이미지 어드민"""
    list_display = ('meetup', 'original_name', 'view_image_button', 'file_size_display', 'width', 'height', 'order', 'uploaded_at')
    list_filter = ('uploaded_at', 'meetup__store')
    search_fields = ('meetup__name', 'meetup__store__store_name', 'original_name')
    readonly_fields = ('image_preview', 'file_url', 'file_path', 'file_size', 'width', 'height', 'uploaded_at', 'uploaded_by')
    ordering = ('meetup', 'order', 'uploaded_at')
    list_per_page = 10
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('meetup', 'original_name', 'order')
        }),
        ('이미지 정보', {
            'fields': ('image_preview', 'width', 'height', 'file_size_display')
        }),
        ('파일 정보', {
            'fields': ('file_url', 'file_path'),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('uploaded_at', 'uploaded_by'),
            'classes': ('collapse',)
        }),
    )
    
    def view_image_button(self, obj):
        """이미지 보기 버튼 (모달 방식) - 아이콘만 표시"""
        if obj and obj.file_url:
            return format_html(
                '<button type="button" class="button" onclick="showImageModal(\'{}\', \'{}\')" style="background-color: #007cba; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;" title="이미지 보기">'
                '<i class="fas fa-eye"></i>'
                '</button>',
                obj.file_url,
                obj.original_name
            )
        return "이미지 없음"
    view_image_button.short_description = '이미지'
    
    def file_size_display(self, obj):
        """파일 크기 표시"""
        if obj:
            return obj.get_file_size_display()
        return ""
    file_size_display.short_description = '파일 크기'
    
    def image_preview(self, obj):
        """이미지 미리보기"""
        if obj and obj.file_url:
            return format_html(
                '<img src="{}" alt="{}" style="max-width: 200px; max-height: 200px; object-fit: contain; cursor: pointer;" onclick="showImageModal(\'{}\', \'{}\')" title="클릭하여 크게 보기">',
                obj.file_url,
                obj.original_name,
                obj.file_url,
                obj.original_name
            )
        return "이미지 없음"
    image_preview.short_description = '이미지 미리보기'

@admin.register(MeetupOption)
class MeetupOptionAdmin(admin.ModelAdmin):
    list_display = ['meetup', 'name', 'is_required', 'choices_count', 'order', 'created_at']
    list_filter = ['meetup__store', 'is_required', 'created_at']
    search_fields = ['meetup__name', 'name']
    readonly_fields = ['created_at']
    ordering = ['meetup', 'order']
    inlines = [MeetupChoiceInline]
    
    def choices_count(self, obj):
        """선택지 수"""
        return obj.choices.count()
    choices_count.short_description = '선택지 수'

@admin.register(MeetupChoice)
class MeetupChoiceAdmin(admin.ModelAdmin):
    list_display = ['option', 'name', 'additional_price_display', 'order', 'created_at']
    list_filter = ['option__meetup__store', 'created_at']
    search_fields = ['option__meetup__name', 'option__name', 'name']
    readonly_fields = ['created_at']
    ordering = ['option', 'order']
    
    def additional_price_display(self, obj):
        """추가요금 표시"""
        if obj.additional_price > 0:
            return f"+{obj.additional_price:,} sats"
        elif obj.additional_price < 0:
            return f"{obj.additional_price:,} sats"
        return "무료"
    additional_price_display.short_description = '추가요금'
