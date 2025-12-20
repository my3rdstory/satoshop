from django.contrib import admin

from .models import DiscordBot, DiscordChannel


class DiscordChannelInline(admin.TabularInline):
    model = DiscordChannel
    extra = 1
    fields = ('server_name', 'channel_name', 'channel_id', 'is_active')


@admin.register(DiscordBot)
class DiscordBotAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    fields = ('name', 'token', 'is_active')
    inlines = [DiscordChannelInline]
