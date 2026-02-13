from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html

from .forms import ApiKeyAdminForm
from .models import ApiAllowedOrigin, ApiIpAllowlist, ApiKey


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    form = ApiKeyAdminForm
    list_display = (
        "name",
        "auth_method",
        "nostr_pubkey_short",
        "channel_slug",
        "key_prefix",
        "is_active",
        "scopes",
        "created_by",
        "created_at",
        "last_used_at",
        "view_orders_link",
    )
    list_filter = ("is_active", "auth_method", "scopes", "channel_slug", "created_by")
    search_fields = ("name", "key_prefix", "channel_slug", "nostr_pubkey")
    readonly_fields = ("auth_method", "nostr_pubkey", "key_prefix", "key_hash", "created_by", "created_at", "updated_at", "last_used_at")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "channel_slug",
                    "scopes",
                    "is_active",
                )
            },
        ),
        (
            "Nostr 인증 설정",
            {
                "fields": (
                    "use_nostr_auth",
                    "nostr_pubkey_input",
                    "auth_method",
                    "nostr_pubkey",
                )
            },
        ),
        (
            "발급 정보",
            {
                "fields": (
                    "key_prefix",
                    "key_hash",
                    "created_by",
                    "created_at",
                    "updated_at",
                    "last_used_at",
                )
            },
        ),
    )
    actions = ("activate_keys", "deactivate_keys", "regenerate_keys")

    def save_model(self, request, obj, form, change):
        previous_auth_method = None
        if change and obj.pk:
            previous_auth_method = ApiKey.objects.filter(pk=obj.pk).values_list("auth_method", flat=True).first()

        if form.cleaned_data.get("use_nostr_auth"):
            obj.auth_method = ApiKey.AUTH_METHOD_NOSTR
            obj.nostr_pubkey = form.cleaned_data.get("normalized_nostr_pubkey", "")
        else:
            obj.auth_method = ApiKey.AUTH_METHOD_API_KEY
            obj.nostr_pubkey = ""

        generated_key = None
        should_generate_key = (
            (not change)
            or (not obj.key_hash)
            or (
                previous_auth_method == ApiKey.AUTH_METHOD_NOSTR
                and obj.auth_method == ApiKey.AUTH_METHOD_API_KEY
            )
        )
        if should_generate_key:
            generated_key = ApiKey.generate_raw_key()
            obj.set_key(generated_key)
        if not obj.created_by:
            obj.created_by = request.user

        super().save_model(request, obj, form, change)
        if generated_key and obj.auth_method == ApiKey.AUTH_METHOD_API_KEY:
            self.message_user(
                request,
                (
                    "신규 API 키가 발급되었습니다. 아래 키를 안전한 곳에 저장하세요. "
                    "다시 조회할 수 없습니다:\n"
                    f"{generated_key}"
                ),
                level=messages.SUCCESS,
            )
        elif obj.auth_method == ApiKey.AUTH_METHOD_NOSTR:
            self.message_user(
                request,
                (
                    "Nostr 인증 API 키가 저장되었습니다. "
                    "이 키는 Bearer 인증을 무시하고 Nostr 서명 인증만 허용합니다."
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
        skipped_nostr = 0
        for key in queryset:
            if key.uses_nostr_auth:
                skipped_nostr += 1
                continue
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
        if skipped_nostr:
            self.message_user(
                request,
                f"Nostr 인증 키 {skipped_nostr}개는 재발급 대상에서 제외했습니다.",
                level=messages.WARNING,
            )

    def view_orders_link(self, obj):
        channel = obj.channel_slug or f"api-{obj.key_prefix}"
        url = reverse("api:channel_sales") + f"?channel={channel}"
        return format_html('<a class="button" href="{}" target="_blank" rel="noopener noreferrer">판매 목록 보기</a>', url)
    view_orders_link.short_description = "판매 목록"

    def nostr_pubkey_short(self, obj):
        if not obj.nostr_pubkey:
            return "-"
        return f"{obj.nostr_pubkey[:12]}...{obj.nostr_pubkey[-8:]}"
    nostr_pubkey_short.short_description = "Nostr 공개키"


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
