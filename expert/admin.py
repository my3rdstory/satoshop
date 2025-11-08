from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html
from django.utils import timezone

from .models import (
    Contract,
    ContractParticipant,
    ContractMessage,
    ContractEmailLog,
    ContractTemplate,
    ExpertEmailSettings,
    DirectContractStageLog,
)
from .services import generate_chat_archive_pdf


@admin.action(description="채팅 로그 PDF 생성")
def generate_chat_pdf(modeladmin, request, queryset):
    success_count = 0
    for contract in queryset:
        try:
            generate_chat_archive_pdf(contract)
            success_count += 1
        except RuntimeError as exc:
            messages.error(request, f"{contract.title}: {exc}")
        except Exception as exc:  # pylint: disable=broad-except
            messages.error(request, f"{contract.title}: 예기치 못한 오류 - {exc}")
    if success_count:
        messages.success(request, f"{success_count}건의 채팅 PDF를 생성했습니다.")


class ContractParticipantInline(admin.TabularInline):
    model = ContractParticipant
    extra = 0
    fields = ("user", "role", "lightning_identifier", "is_confirmed", "signed_at")
    readonly_fields = ("signed_at",)


class ContractMessageInline(admin.TabularInline):
    model = ContractMessage
    extra = 0
    fields = ("created_at", "sender", "sender_role", "message_type", "content")
    readonly_fields = ("created_at", "sender", "sender_role", "message_type", "content")
    can_delete = False


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "created_by__username")
    readonly_fields = ("public_id", "created_at", "updated_at", "archive_generated_at")
    inlines = [ContractParticipantInline, ContractMessageInline]
    actions = [generate_chat_pdf]


@admin.register(ContractEmailLog)
class ContractEmailLogAdmin(admin.ModelAdmin):
    list_display = ("contract", "subject", "sent_at", "success")
    list_filter = ("success", "sent_at")
    search_fields = ("contract__title", "subject", "recipients")
    readonly_fields = ("contract", "recipients", "subject", "message", "sent_at", "success", "error_message")


@admin.register(ExpertEmailSettings)
class ExpertEmailSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "계약 이메일 SMTP(Gmail) 설정",
            {
                "fields": (
                    "expert_gmail_address",
                    "expert_gmail_app_password",
                    "expert_email_sender_name",
                    "gmail_help_url",
                ),
                "description": (
                    "Gmail 2단계 인증을 활성화한 뒤 <em>앱 비밀번호</em>를 생성해 입력하세요. "
                    "앱 비밀번호는 공백 없이 16자를 입력해야 하며, 가능하면 전용 Gmail 계정을 사용하는 것이 좋습니다."
                ),
            },
        ),
    )
    list_display = ("expert_gmail_address", "expert_email_sender_name")

    def has_add_permission(self, request):  # pragma: no cover - admin guard
        # Gmail 설정이 아직 없다면 최초 1회 등록을 허용한다.
        return not ExpertEmailSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):  # pragma: no cover - admin guard
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not qs.exists():
            from myshop.models import SiteSettings  # local import to avoid circular during startup
            SiteSettings.get_settings()
            qs = super().get_queryset(request)
        return qs

    def changelist_view(self, request, extra_context=None):  # pragma: no cover - admin redirect helper
        qs = self.get_queryset(request)
        if qs.count() == 1:
            obj = qs.first()
            return redirect(reverse("admin:expert_expertemailsettings_change", args=[obj.pk]))
        return super().changelist_view(request, extra_context)


@admin.action(description="계약 조건 입력 화면에 노출")
def activate_template(modeladmin, request, queryset):
    template = queryset.first()
    if not template:
        messages.warning(request, "선택된 계약서가 없습니다.")
        return
    template.is_selected = True
    template.save()
    if queryset.count() > 1:
        messages.warning(request, "첫 번째 선택 항목만 노출 대상으로 설정했습니다.")
    else:
        messages.success(request, f"'{template}' 계약서를 노출 대상으로 설정했습니다.")


@admin.register(ContractTemplate)
class ContractTemplateAdmin(admin.ModelAdmin):
    list_display = ("title", "version_label", "is_selected", "updated_at")
    list_filter = ("is_selected", "created_at")
    search_fields = ("title", "version_label", "content")
    actions = [activate_template]
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "기본 정보",
            {
                "fields": ("title", "version_label", "is_selected"),
                "description": "계약서 이름과 버전을 관리하고, 노출 여부를 선택하세요.",
            },
        ),
        (
            "마크다운 본문",
            {
                "fields": ("content",),
                "description": "MD 포맷으로 작성된 계약서 내용을 입력하세요.",
            },
        ),
        (
            "메타데이터",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )


@admin.register(DirectContractStageLog)
class DirectContractStageLogAdmin(admin.ModelAdmin):
    list_display = (
        "document_link",
        "stage_draft",
        "stage_role_one",
        "stage_role_two",
        "stage_completed",
        "latest_activity",
    )
    search_fields = ("document__slug", "document__payload__title")
    readonly_fields = ("document", "token", "stage", "started_at", "meta")
    list_display_links = ("document_link",)
    list_per_page = 25

    stage_labels = {
        "draft": "드래프트",
        "role_one": "역할 1",
        "role_two": "역할 2",
        "completed": "완료",
    }

    def get_queryset(self, request):
        qs = (
            super()
            .get_queryset(request)
            .exclude(document__isnull=True)
            .select_related("document")
            .prefetch_related("document__stage_logs")
            .order_by("document_id", "-started_at")
            .distinct("document_id")
        )
        return qs

    def document_link(self, obj):
        if not obj.document:
            return "-"
        title = obj.document.payload.get("title") if obj.document.payload else obj.document.slug
        try:
            url = reverse("admin:expert_directcontractdocument_change", args=[obj.document.pk])
            return format_html('<a href="{}">{} ({})</a>', url, title or obj.document.slug, obj.document.slug)
        except NoReverseMatch:
            return f"{title or obj.document.slug} ({obj.document.slug})"

    document_link.short_description = "계약"

    def _stage_map(self, obj):
        if not hasattr(obj, "_stage_cache"):
            logs = obj.document.stage_logs.all() if obj.document else []
            obj._stage_cache = {log.stage: log for log in logs}
        return obj._stage_cache

    def _render_stage(self, obj, stage_key):
        stage_map = self._stage_map(obj)
        log = stage_map.get(stage_key)
        label = self.stage_labels.get(stage_key, stage_key)
        if not log:
            return format_html('<span style="color:#f97316;">{} · 대기</span>', label)
        ts = timezone.localtime(log.started_at).strftime("%Y-%m-%d %H:%M")
        meta = log.meta or {}
        detail = meta.get("role") or meta.get("title") or "완료"
        return format_html('<strong>{}</strong><br><span class="text-muted">{}</span>', ts, detail)

    def stage_draft(self, obj):
        return self._render_stage(obj, "draft")

    stage_draft.short_description = "1단계"

    def stage_role_one(self, obj):
        return self._render_stage(obj, "role_one")

    stage_role_one.short_description = "2단계"

    def stage_role_two(self, obj):
        return self._render_stage(obj, "role_two")

    stage_role_two.short_description = "3단계"

    def stage_completed(self, obj):
        return self._render_stage(obj, "completed")

    stage_completed.short_description = "4단계"

    def latest_activity(self, obj):
        stage_map = self._stage_map(obj)
        if not stage_map:
            return "-"
        latest = max(stage_map.values(), key=lambda log: log.started_at)
        return timezone.localtime(latest.started_at).strftime("%Y-%m-%d %H:%M")

    latest_activity.short_description = "마지막 기록"
