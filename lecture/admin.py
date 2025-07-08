from django.contrib import admin
from .models import Category, Lecture, LectureEnrollment, LectureReview, LiveLecture, LiveLectureImage, LiveLectureOrder


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
    ordering = ['-created_at']


@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'instructor', 'difficulty', 'price', 'status', 'enrolled_count', 'start_date']
    list_filter = ['category', 'difficulty', 'status', 'created_at']
    search_fields = ['title', 'instructor__username', 'instructor__first_name', 'instructor__last_name']
    ordering = ['-created_at']
    readonly_fields = ['enrolled_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('title', 'description', 'category', 'instructor')
        }),
        ('강의 설정', {
            'fields': ('difficulty', 'duration', 'max_students', 'price', 'status')
        }),
        ('일정', {
            'fields': ('start_date', 'end_date')
        }),
        ('이미지', {
            'fields': ('thumbnail',)
        }),
        ('통계', {
            'fields': ('enrolled_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LectureEnrollment)
class LectureEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['lecture', 'student', 'status', 'enrolled_at']
    list_filter = ['status', 'enrolled_at', 'lecture__category']
    search_fields = ['lecture__title', 'student__username', 'student__first_name', 'student__last_name']
    ordering = ['-enrolled_at']
    readonly_fields = ['enrolled_at']


@admin.register(LectureReview)
class LectureReviewAdmin(admin.ModelAdmin):
    list_display = ['lecture', 'student', 'rating', 'created_at']
    list_filter = ['rating', 'created_at', 'lecture__category']
    search_fields = ['lecture__title', 'student__username', 'comment']
    ordering = ['-created_at']
    readonly_fields = ['created_at']


class LiveLectureImageInline(admin.TabularInline):
    model = LiveLectureImage
    extra = 0
    readonly_fields = ['file_size', 'width', 'height', 'uploaded_at', 'uploaded_by']


@admin.register(LiveLecture)
class LiveLectureAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'price_display', 'display_price', 'max_participants', 'current_participants', 'is_active', 'date_time']
    list_filter = ['price_display', 'is_active', 'is_temporarily_closed', 'created_at', 'store']
    search_fields = ['name', 'store__store_name', 'instructor_email']
    ordering = ['-created_at']
    readonly_fields = ['current_participants', 'created_at', 'updated_at']
    inlines = [LiveLectureImageInline]
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('store', 'name', 'description', 'date_time', 'special_notes')
        }),
        ('강사 정보', {
            'fields': ('instructor_contact', 'instructor_email', 'instructor_chat_channel')
        }),
        ('정원 설정', {
            'fields': ('max_participants', 'no_limit', 'current_participants')
        }),
        ('가격 설정', {
            'fields': ('price_display', 'price', 'price_krw')
        }),
        ('할인 설정', {
            'fields': ('is_discounted', 'discounted_price', 'discounted_price_krw', 'early_bird_end_date', 'early_bird_end_time'),
            'classes': ('collapse',)
        }),
        ('상태', {
            'fields': ('is_active', 'is_temporarily_closed')
        }),
        ('안내 메시지', {
            'fields': ('completion_message',),
            'classes': ('collapse',)
        }),
        ('시스템 정보', {
            'fields': ('created_at', 'updated_at', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """삭제된 라이브 강의는 목록에서 제외"""
        return super().get_queryset(request).filter(deleted_at__isnull=True)
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # 수정 시
            return self.readonly_fields + ['store']
        return self.readonly_fields


@admin.register(LiveLectureImage)
class LiveLectureImageAdmin(admin.ModelAdmin):
    list_display = ['live_lecture', 'original_name', 'file_size_display', 'width', 'height', 'uploaded_at']
    list_filter = ['uploaded_at', 'live_lecture__store']
    search_fields = ['live_lecture__name', 'original_name']
    ordering = ['-uploaded_at']
    readonly_fields = ['file_size', 'width', 'height', 'uploaded_at', 'uploaded_by']
    
    def file_size_display(self, obj):
        return obj.get_file_size_display()
    file_size_display.short_description = '파일 크기'


@admin.register(LiveLectureOrder)
class LiveLectureOrderAdmin(admin.ModelAdmin):
    list_display = ['live_lecture', 'user', 'status', 'price', 'is_early_bird', 'paid_at', 'created_at']
    list_filter = ['status', 'is_early_bird', 'created_at', 'live_lecture__store']
    search_fields = ['live_lecture__name', 'user__username', 'user__email', 'order_number']
    ordering = ['-created_at']
    readonly_fields = ['order_number', 'created_at', 'updated_at', 'paid_at', 'confirmed_at']
    
    fieldsets = (
        ('주문 정보', {
            'fields': ('live_lecture', 'user', 'order_number', 'status')
        }),
        ('가격 정보', {
            'fields': ('price', 'is_early_bird', 'discount_rate', 'original_price')
        }),
        ('결제 정보', {
            'fields': ('payment_hash', 'payment_request', 'paid_at'),
            'classes': ('collapse',)
        }),
        ('참가 정보', {
            'fields': ('confirmed_at', 'confirmation_message_sent', 'attended', 'attended_at')
        }),
        ('임시 예약', {
            'fields': ('is_temporary_reserved', 'reservation_expires_at', 'auto_cancelled_reason'),
            'classes': ('collapse',)
        }),
        ('시스템 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # 수정 시
            return self.readonly_fields + ['live_lecture', 'user']
        return self.readonly_fields
