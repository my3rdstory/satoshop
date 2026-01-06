from django.contrib import admin

from .models import Minihome


@admin.register(Minihome)
class MinihomeAdmin(admin.ModelAdmin):
    list_display = ("slug", "display_name", "is_published", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("slug", "display_name", "owners__username", "owners__email")
    filter_horizontal = ("owners",)
