from django.contrib import admin, messages

from .models import ApiAllowedOrigin, ApiIpAllowlist, ApiKey


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "key_prefix",
        "is_active",
        "scopes",
        "created_by",
        "created_at",
        "last_used_at",
    )
    list_filter = ("is_active", "scopes", "created_by")
    search_fields = ("name", "key_prefix")
    readonly_fields = ("key_prefix", "key_hash", "created_at", "updated_at", "last_used_at")
    actions = ("activate_keys", "deactivate_keys", "regenerate_keys")

    def save_model(self, request, obj, form, change):
        generated_key = None
        if not change or not obj.key_hash:
            generated_key = ApiKey.generate_raw_key()
            obj.set_key(generated_key)
            if not obj.created_by:
                obj.created_by = request.user
        super().save_model(request, obj, form, change)
        if generated_key:
            self.message_user(
                request,
                (
                    "신규 API 키가 발급되었습니다. 아래 키를 안전한 곳에 저장하세요. "
                    "다시 조회할 수 없습니다:\n"
                    f"{generated_key}"
                ),
                level=messages.SUCCESS,
            )

    @admin.action(description="선택한 키 비활성화")
    def deactivate_keys(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated}개의 API 키를 비활성화했습니다.", level=messages.WARNING)

    @admin.action(description="선택한 키 활성화")
    def activate_keys(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated}개의 API 키를 활성화했습니다.", level=messages.SUCCESS)

    @admin.action(description="선택한 키 재발급(기존 키 즉시 폐기)")
    def regenerate_keys(self, request, queryset):
        regenerated_messages = []
        for key in queryset:
            raw_key = ApiKey.generate_raw_key()
            key.set_key(raw_key)
            key.save(update_fields=["key_prefix", "key_hash", "updated_at"])
            regenerated_messages.append(f"{key.name} → {raw_key}")
        if regenerated_messages:
            self.message_user(
                request,
                "다음 키가 재발급되었습니다(기존 키는 즉시 폐기됨):\n" + "\n".join(regenerated_messages),
                level=messages.SUCCESS,
            )


@admin.register(ApiIpAllowlist)
class ApiIpAllowlistAdmin(admin.ModelAdmin):
    list_display = ("name", "cidr", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "cidr")
    readonly_fields = ("created_at",)


@admin.register(ApiAllowedOrigin)
class ApiAllowedOriginAdmin(admin.ModelAdmin):
    list_display = ("name", "origin", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "origin")
    readonly_fields = ("created_at",)
