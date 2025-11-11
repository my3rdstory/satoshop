import json

from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html, format_html_join
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import (
    ContractTemplate,
    ExpertEmailSettings,
    DirectContractStageLog,
    ContractPricingSetting,
)


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


@admin.register(ContractPricingSetting)
class ContractPricingSettingAdmin(admin.ModelAdmin):
    list_display = ("name", "enabled", "client_fee_sats", "performer_fee_sats", "updated_at")
    readonly_fields = ("updated_at",)
    fieldsets = (
        (
            "기본 정보",
            {
                "fields": ("name", "enabled", "description"),
                "description": "활성화 여부와 정책 설명을 입력하세요.",
            },
        ),
        (
            "계약 금액",
            {
                "fields": ("client_fee_sats", "performer_fee_sats"),
                "description": "각 역할이 부담해야 하는 사토시 금액을 설정합니다.",
            },
        ),
        ("변경 이력", {"fields": ("updated_at",)}),
    )

    def has_add_permission(self, request):
        if ContractPricingSetting.objects.count() >= 1:
            return False
        return super().has_add_permission(request)


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
    readonly_fields = ("document", "token", "stage", "stage_display", "started_at", "hash_comparison", "meta_details")
    list_display_links = ("document_link",)
    list_per_page = 25
    ordering = ("-started_at",)
    exclude = ("meta",)
    fieldsets = (
        (
            "기본 정보",
            {
                "fields": ("document", "token", "stage_display", "started_at"),
            },
        ),
        (
            "해시 비교",
            {
                "fields": ("hash_comparison",),
            },
        ),
        (
            "메타 정보",
            {
                "fields": ("meta_details",),
            },
        ),
    )

    def get_queryset(self, request):
        qs = (
            super()
            .get_queryset(request)
            .select_related("document")
            .order_by("-started_at")
        )
        return qs

    stage_labels = {
        "draft": "드래프트",
        "role_one": "역할 1",
        "role_two": "역할 2",
        "completed": "완료",
    }

    def stage_display(self, obj):
        return self.stage_labels.get(obj.stage, obj.stage)

    stage_display.short_description = "단계"

    stage_meta_fields = {
        "draft": (
            ("title", "계약 제목"),
            ("payment_type", "결제 방식"),
            ("lightning_id", "라이트닝 ID"),
        ),
        "role_one": (
            ("role", "역할"),
            ("role_label", "역할 라벨"),
            ("email", "이메일"),
            ("lightning_id", "라이트닝 ID"),
            ("signed_at", "서명 시각"),
        ),
        "role_two": (
            ("role", "역할"),
            ("role_label", "역할 라벨"),
            ("email", "이메일"),
            ("lightning_id", "라이트닝 ID"),
            ("signed_at", "서명 시각"),
        ),
        "completed": (),
    }
    payment_field_order = (
        "amount_sats",
        "paid_at",
        "payment_hash",
        "payment_request",
    )
    payment_field_labels = {
        "amount_sats": "결제 금액 (sats)",
        "paid_at": "결제 완료 시각",
        "payment_hash": "결제 해시",
        "payment_request": "결제 요청",
    }

    def meta_details(self, obj):
        if not obj:
            return "-"
        rows = self._build_meta_rows(obj)
        if not rows:
            return "기록된 메타 정보가 없습니다."
        rows_html = format_html_join("", "{}", ((row,) for row in rows))
        return format_html(
            '<div style="border:1px solid #e2e8f0;border-radius:8px;padding:16px;background:#f8fafc;">{}</div>',
            rows_html,
        )

    meta_details.short_description = "메타 정보"

    def _build_meta_rows(self, obj):
        meta = obj.meta or {}
        rows = []
        # stage별로 구분된 필드 렌더링
        for stage_key, fields in self.stage_meta_fields.items():
            stage_meta = meta if obj.stage == stage_key else meta.get(stage_key, {})
            if not stage_meta:
                continue
            rows.append(
                format_html(
                    '<div style="margin:12px 0;font-weight:600;color:#1e293b;">[{} 단계]</div>',
                    self.stage_labels.get(stage_key, stage_key),
                )
            )
            for key, label in fields:
                value = stage_meta.get(key)
                if not value:
                    continue
                rows.append(self._render_meta_row(label, value))
            payment_meta = stage_meta.get("payment")
            if isinstance(payment_meta, dict):
                for key in self.payment_field_order:
                    if key not in payment_meta:
                        continue
                    rows.append(
                        self._render_meta_row(
                            self.payment_field_labels.get(key, f"결제 {key}"),
                            payment_meta.get(key),
                        )
                    )
        return rows

    def _render_meta_row(self, label, value):
        return format_html(
            '<div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:8px;">'
            '<span style="width:140px;font-weight:600;color:#475569;">{}</span>'
            '<span style="flex:1;word-break:break-word;">{}</span>'
            "</div>",
            label,
            self._render_meta_value(value),
        )

    def _render_meta_value(self, value):
        if value in (None, ""):
            return "-"
        if isinstance(value, bool):
            return "예" if value else "아니오"
        if isinstance(value, (dict, list)):
            pretty = json.dumps(value, ensure_ascii=False, indent=2)
            return format_html('<pre style="margin:0;white-space:pre-wrap;">{}</pre>', pretty)
        return format_html("{}", value)

    def get_queryset(self, request):
        qs = (
            super()
            .get_queryset(request)
            .filter(stage="draft")
            .select_related("document")
            .prefetch_related("document__stage_logs")
            .order_by("-started_at")
        )
        return qs

    def document_link(self, obj):
        if obj.document:
            title = obj.document.payload.get("title") if obj.document.payload else obj.document.slug
            try:
                url = reverse("admin:expert_directcontractdocument_change", args=[obj.document.pk])
                return format_html('<a href="{}">{} ({})</a>', url, title or obj.document.slug, obj.document.slug)
            except NoReverseMatch:
                return f"{title or obj.document.slug} ({obj.document.slug})"
        review_url = reverse("expert:direct-review", kwargs={"token": obj.token})
        title = (obj.meta or {}).get("title") or obj.token
        return format_html('<a href="{}" target="_blank">{} (초안)</a>', review_url, title)

    document_link.short_description = "계약"

    def _stage_map(self, obj):
        if not hasattr(obj, "_stage_cache"):
            if obj.document:
                logs = obj.document.stage_logs.all()
            else:
                logs = DirectContractStageLog.objects.filter(token=obj.token).order_by("started_at")
            cache = {log.stage: log for log in logs}
            cache.setdefault("draft", obj)
            obj._stage_cache = cache
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
        payment_html = ""
        payment_meta = self._get_payment_receipt(obj, stage_key=stage_key)
        if stage_key == "draft":
            payment_meta = None
        if payment_meta:
            payment_html = self._render_payment_badge(payment_meta)
        return format_html(
            '<strong>{}</strong><br><span class="text-muted">{}</span>{}',
            ts,
            detail,
            format_html("<br>{}", payment_html) if payment_html else "",
        )

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

    def _render_payment_badge(self, payment_meta: dict) -> str:
        amount = payment_meta.get("amount_sats") or 0
        paid_at_raw = payment_meta.get("paid_at")
        paid_display = ""
        if paid_at_raw:
            paid_dt = parse_datetime(paid_at_raw)
            if paid_dt:
                if timezone.is_naive(paid_dt):
                    paid_dt = timezone.make_aware(paid_dt, timezone=timezone.utc)
                paid_display = timezone.localtime(paid_dt).strftime("%Y-%m-%d %H:%M")
        payment_hash = payment_meta.get("payment_hash")
        hash_display = f" · #{payment_hash[:10]}" if payment_hash else ""
        subtitle = f" ({paid_display})" if paid_display else ""
        return format_html(
            '<span style="color:#facc15;font-weight:600;">⚡ {} sats 결제{}{}</span>',
            amount,
            subtitle,
            hash_display,
        )

    def _get_payment_receipt(self, obj, *, stage_key: str):
        stage_map = self._stage_map(obj)
        log = stage_map.get(stage_key)
        if log:
            meta_payment = (log.meta or {}).get("payment")
            if meta_payment:
                return meta_payment
        if not obj.document:
            return None
        if stage_key in ("draft", "role_one"):
            return (obj.document.payment_meta or {}).get(obj.document.creator_role)
        if stage_key == "role_two":
            return (obj.document.payment_meta or {}).get(obj.document.counterparty_role)
        return None
    def hash_comparison(self, obj):
        document = obj.document
        if not document:
            return "-"
        rows = []
        rows.append(("PDF 저장된 해시", document.final_pdf_hash or "(없음)"))
        rows.append(("생성자 해시", document.creator_hash or "(없음)"))
        rows.append(("수행자 해시", document.counterparty_hash or "(없음)"))
        rows.append(("중개자 해시", document.mediator_hash or "(없음)"))
        table = format_html(
            '<table class="hash-table">{}</table>',
            format_html_join(
                "",
                "<tr><th>{}</th><td><code>{}</code></td></tr>",
                rows,
            ),
        )
        return table

    hash_comparison.short_description = "해시 비교"
