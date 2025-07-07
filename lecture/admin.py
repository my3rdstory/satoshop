from django.contrib import admin
from .models import Category, Lecture, LectureEnrollment, LectureReview


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
