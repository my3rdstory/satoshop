from django.contrib import admin

from .models import DiscordBot, DiscordChannel


class DiscordChannelInline(admin.TabularInline):
    model = DiscordChannel
    extra = 1
    fields = ('server_name', 'channel_name', 'channel_id', 'is_active')


@admin.register(DiscordBot)
class DiscordBotAdmin(admin.ModelAdmin):
    list_display = ('name', 'application_id', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'application_id')
    fields = ('name', 'application_id', 'public_key', 'token', 'is_active')
    inlines = [DiscordChannelInline]
