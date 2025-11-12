import json
from datetime import datetime

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
    ExpertBlinkRevenueStats,
    ExpertUsageStats,
)
from .stats import aggregate_payment_stats, aggregate_usage_stats


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
    list_display = ("name", "enabled", "client_fee_sats", "performer_fee_sats")
    readonly_fields: tuple = ()
    fieldsets = (
        (
            "기본 정보",
            {
                "fields": ("name", "enabled"),
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


@admin.register(ExpertBlinkRevenueStats)
class BlinkRevenueStatsAdmin(admin.ModelAdmin):
    change_list_template = "admin/expert/blink_revenue_stats.html"
    list_display = ()

    def get_queryset(self, request):
        return self.model.objects.none()

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        context = extra_context or {}
        month_slug = request.GET.get("month") or None
        context["stats"] = aggregate_payment_stats(month_slug=month_slug)
        context["selected_month"] = month_slug or ""
        context["title"] = "Blink 수수료 통계"
        return super().changelist_view(request, extra_context=context)


@admin.register(ExpertUsageStats)
class ExpertUsageStatsAdmin(admin.ModelAdmin):
    change_list_template = "admin/expert/usage_stats.html"
    list_display = ()

    def get_queryset(self, request):
        return self.model.objects.none()

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        context = extra_context or {}
        context["stats"] = aggregate_usage_stats()
        context["title"] = "Expert 사용 통계"
        return super().changelist_view(request, extra_context=context)


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
    readonly_fields = (
        "document",
        "token",
        "stage",
        "stage_display",
        "started_at",
        "hash_comparison",
        "participant_overview",
    )
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
            "참여자 요약",
            {
                "fields": ("participant_overview",),
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

    stage_order = ("draft", "role_one", "role_two", "completed")
    stage_labels = {
        "draft": "드래프트",
        "role_one": "역할 1",
        "role_two": "역할 2",
        "completed": "완료",
    }

    def stage_display(self, obj):
        current_stage = self._resolve_current_stage(obj)
        return self.stage_labels.get(current_stage, current_stage)

    stage_display.short_description = "단계"

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

    def participant_overview(self, obj):
        if not obj:
            return "-"
        document = obj.document
        if document:
            participants = [
                {
                    "label": "생성자",
                    "stage_key": "role_one",
                    "user": document.creator,
                    "role_display": document.get_creator_role_display(),
                    "email": document.creator_email or getattr(document.creator, "email", None),
                },
                {
                    "label": "상대방",
                    "stage_key": "role_two",
                    "user": document.counterparty_user,
                    "role_display": document.get_counterparty_role_display(),
                    "email": document.counterparty_email or getattr(document.counterparty_user, "email", None),
                },
            ]
        else:
            participants = [
                {"label": "생성자", "stage_key": "role_one"},
                {"label": "상대방", "stage_key": "role_two"},
            ]
        panels = [self._render_participant_panel(obj, **config) for config in participants]
        panels = [panel for panel in panels if panel]
        if not panels:
            return "참여자 정보가 없습니다."
        return format_html(
            '<div style="display:flex;flex-direction:column;gap:16px;">{}</div>',
            format_html_join("", "{}", ((panel,) for panel in panels)),
        )

    participant_overview.short_description = "계약 참여자"

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

    def _resolve_current_stage(self, obj):
        stage_map = self._stage_map(obj)
        for stage_key in reversed(self.stage_order):
            if stage_map.get(stage_key):
                return stage_key
        return "draft"

    def _render_participant_panel(
        self,
        obj,
        *,
        label: str,
        stage_key: str,
        role_display: str | None = None,
        user=None,
        email: str | None = None,
    ):
        stage_map = self._stage_map(obj)
        log = stage_map.get(stage_key)
        stage_meta = (log.meta or {}) if log else {}
        display_role = role_display or stage_meta.get("role_label") or stage_meta.get("role") or "-"
        resolved_email = email or stage_meta.get("email")
        lightning_id = stage_meta.get("lightning_id")
        signed_at = stage_meta.get("signed_at")

        login_rows = []
        if user:
            login_rows.append(self._render_meta_row("계정", f"{user} (ID {user.pk})"))
        if resolved_email:
            login_rows.append(self._render_meta_row("이메일", resolved_email))
        if lightning_id:
            login_rows.append(self._render_meta_row("라이트닝 ID", lightning_id))
        if signed_at:
            login_rows.append(self._render_meta_row("서명 시각", self._format_meta_datetime(signed_at)))
        if not login_rows:
            login_rows.append(self._render_meta_row("상태", "로그인 정보가 없습니다."))

        payment_meta = self._get_payment_receipt(obj, stage_key=stage_key)
        payment_rows = []
        if payment_meta:
            for key in self.payment_field_order:
                value = payment_meta.get(key)
                if not value:
                    continue
                if key == "paid_at":
                    value = self._format_meta_datetime(value)
                payment_rows.append(
                    self._render_meta_row(
                        self.payment_field_labels.get(key, f"결제 {key}"),
                        value,
                    )
                )
        if not payment_rows:
            payment_rows.append(self._render_meta_row("상태", "결제 정보가 없습니다."))

        sections = [
            self._render_info_group("로그인 정보", login_rows),
            self._render_info_group("결제 정보", payment_rows),
        ]
        panel_body = format_html_join("", "{}", ((section,) for section in sections if section))
        return format_html(
            '<div style="border:1px solid #cbd5f5;border-radius:12px;padding:16px;background:#f8fafc;">'
            '<div style="font-size:14px;font-weight:600;color:#0f172a;margin-bottom:8px;">{} '
            '<span style="color:#64748b;font-weight:500;">{}</span></div>{}'
            "</div>",
            label,
            display_role,
            panel_body,
        )

    def _render_info_group(self, title, rows):
        if not rows:
            return ""
        return format_html(
            '<div style="margin-bottom:12px;">'
            '<div style="font-weight:600;color:#1e293b;margin-bottom:6px;">{}</div>'
            '<div style="display:flex;flex-direction:column;gap:4px;">{}</div>'
            "</div>",
            title,
            format_html_join("", "{}", ((row,) for row in rows)),
        )

    def _format_meta_datetime(self, value):
        if not value:
            return "-"
        if isinstance(value, datetime):
            dt = value
        else:
            dt = parse_datetime(value)
        if not dt:
            return value
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone=timezone.utc)
        return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M")

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
