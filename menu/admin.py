from django.contrib import admin
from .models import MenuCategory, Menu, MenuOption

@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'created_at']
    list_filter = ['store', 'created_at']
    search_fields = ['name', 'store__store_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['store', 'name']

class MenuOptionInline(admin.TabularInline):
    model = MenuOption
    extra = 1
    readonly_fields = ['id', 'created_at']

@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'price', 'price_display', 'is_active', 'is_discounted', 'created_at']
    list_filter = ['store', 'price_display', 'is_active', 'is_discounted', 'is_temporarily_out_of_stock', 'created_at']
    search_fields = ['name', 'description', 'store__store_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    filter_horizontal = ['categories']
    inlines = [MenuOptionInline]
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('store', 'name', 'description', 'image', 'categories')
        }),
        ('가격 정보', {
            'fields': ('price_display', 'price', 'is_discounted', 'discounted_price')
        }),
        ('상태 정보', {
            'fields': ('is_active', 'is_temporarily_out_of_stock')
        }),
        ('메타 정보', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )



@admin.register(MenuOption)
class MenuOptionAdmin(admin.ModelAdmin):
    list_display = ['menu', 'name', 'is_required', 'order', 'created_at']
    list_filter = ['menu__store', 'is_required', 'created_at']
    search_fields = ['menu__name', 'name']
    readonly_fields = ['id', 'created_at']
    ordering = ['menu', 'order']
