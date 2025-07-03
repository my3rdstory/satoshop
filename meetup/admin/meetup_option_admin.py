from django.contrib import admin
from ..models import MeetupOption, MeetupChoice


class MeetupChoiceInline(admin.TabularInline):
    """밋업 선택지 인라인 어드민"""
    model = MeetupChoice
    extra = 1
    readonly_fields = ['created_at']
    fields = ('name', 'additional_price', 'order', 'created_at')


# @admin.register(MeetupOption)
# class MeetupOptionAdmin(admin.ModelAdmin):
#     list_display = ['meetup', 'name', 'is_required', 'choices_count', 'order', 'created_at']
#     list_filter = ['meetup__store', 'is_required', 'created_at']
#     search_fields = ['meetup__name', 'name']
#     readonly_fields = ['created_at']
#     ordering = ['meetup', 'order']
#     inlines = [MeetupChoiceInline]
#     
#     def choices_count(self, obj):
#         """선택지 수"""
#         return obj.choices.count()
#     choices_count.short_description = '선택지 수'


# @admin.register(MeetupChoice)
# class MeetupChoiceAdmin(admin.ModelAdmin):
#     list_display = ['option', 'name', 'additional_price_display', 'order', 'created_at']
#     list_filter = ['option__meetup__store', 'created_at']
#     search_fields = ['option__meetup__name', 'option__name', 'name']
#     readonly_fields = ['created_at']
#     ordering = ['option', 'order']
#     
#     def additional_price_display(self, obj):
#         """추가요금 표시"""
#         if obj.additional_price > 0:
#             return f"+{obj.additional_price:,} sats"
#         elif obj.additional_price < 0:
#             return f"{obj.additional_price:,} sats"
#         return "무료"
#     additional_price_display.short_description = '추가요금' 