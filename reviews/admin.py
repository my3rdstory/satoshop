from django.contrib import admin

from .models import Review, ReviewImage


class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 0
    readonly_fields = ('file_url', 'uploaded_at')
    fields = ('original_name', 'file_url', 'order', 'uploaded_at')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'product',
        'author',
        'rating',
        'created_at',
        'updated_at',
    )
    list_filter = ('rating', 'created_at', 'product__store')
    search_fields = ('product__title', 'author__username', 'content')
    ordering = ('-created_at',)
    inlines = (ReviewImageInline,)


@admin.register(ReviewImage)
class ReviewImageAdmin(admin.ModelAdmin):
    list_display = ('review', 'original_name', 'order', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('original_name', 'review__product__title', 'review__author__username')
    ordering = ('review', 'order')
