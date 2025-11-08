import markdown

import json
import uuid
from itertools import zip_longest

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import urlencode
from django.views.generic import TemplateView, FormView

from storage.backends import S3Storage

from .contract_flow import (
    build_counterparty_hash,
    build_creator_hash,
    build_mediator_hash,
    generate_share_slug,
    render_contract_pdf,
)
from .emails import send_direct_contract_document_email
from .models import (
    Contract,
    ContractTemplate,
    ContractParticipant,
    DirectContractDocument,
    DirectContractStageLog,
)
from .forms import ContractDraftForm, ContractReviewForm, CounterpartySignatureForm
from .signature_assets import signature_media_fallback_enabled, store_signature_asset_from_data


def render_contract_markdown(text: str) -> str:
    """계약서 마크다운을 HTML로 안전하게 변환."""

    if not text:
        return ""
    md = markdown.Markdown(
        extensions=[
            "markdown.extensions.fenced_code",
            "markdown.extensions.tables",
            "markdown.extensions.nl2br",
            "markdown.extensions.codehilite",
            "markdown.extensions.sane_lists",
        ],
        extension_configs={
            "markdown.extensions.codehilite": {
                "guess_lang": False,
                "noclasses": True,
            }
        },
        output_format="html5",
    )
    return md.convert(text)


def record_stage_log(stage: str, *, document=None, token: str | None = None, meta: dict | None = None):
    """단계 로그를 생성하거나 갱신."""

    meta = meta or {}
    log = None
    if token:
        log = (
            DirectContractStageLog.objects.filter(stage=stage, token=token)
            .order_by("started_at")
            .first()
        )
    if not log and document:
        log = (
            DirectContractStageLog.objects.filter(stage=stage, document=document)
            .order_by("started_at")
            .first()
        )
    if log:
        update_fields = []
        if document and not log.document_id:
            log.document = document
            update_fields.append("document")
        if token is not None and log.token != (token or ""):
            log.token = token or ""
            update_fields.append("token")
        if meta:
            merged_meta = {**(log.meta or {}), **meta}
            if merged_meta != log.meta:
                log.meta = merged_meta
                update_fields.append("meta")
        if update_fields:
            log.save(update_fields=update_fields)
        return log
    return DirectContractStageLog.objects.create(
        document=document,
        token=token or "",
        stage=stage,
        meta=meta,
    )


class ExpertLandingView(TemplateView):
    """Expert 랜딩 페이지."""

    template_name = "expert/landing.html"


class DirectContractStartView(LoginRequiredMixin, TemplateView):
    """직접 계약 생성 시작 화면 (TODO: 계약 생성 플로우 연결)."""

    template_name = "expert/direct_contract_start.html"
    login_url = reverse_lazy("expert:login")


class DirectContractDraftView(LoginRequiredMixin, FormView):
    """직접 계약 생성 폼 뷰(1차 초안)."""

    template_name = "expert/contract_draft.html"
    form_class = ContractDraftForm
    success_url = reverse_lazy("expert:direct-draft")
    login_url = reverse_lazy("expert:login")
    session_prefix = "expert_direct_contract"

    def dispatch(self, request, *args, **kwargs):
        self.active_contract_template = ContractTemplate.objects.filter(is_selected=True).first()
        self.active_contract_template_html = (
            render_contract_markdown(self.active_contract_template.content)
            if self.active_contract_template
            else ""
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        template = self.active_contract_template
        context["active_contract_template"] = template
        context["contract_generated_at"] = timezone.now()
        return context

    def form_valid(self, form):
        draft_payload = self._build_draft_payload(form)
        token = uuid.uuid4().hex
        session_key = self._session_key(token)
        self.request.session[session_key] = draft_payload
        self.request.session.modified = True
        record_stage_log(
            "draft",
            token=token,
            meta={"title": draft_payload.get("title", ""), "payment_type": draft_payload.get("payment_type")},
        )
        return redirect(reverse("expert:direct-review", kwargs={"token": token}))

    def _session_key(self, token: str) -> str:
        return f"{self.session_prefix}:{token}"

    def _build_draft_payload(self, form):
        data = form.cleaned_data.copy()
        for field_name in ("start_date", "end_date", "one_time_due_date"):
            value = data.get(field_name)
            if value:
                data[field_name] = value.isoformat()
        for field_name in ("client_lightning_address", "performer_lightning_address", "one_time_condition"):
            value = data.get(field_name)
            if isinstance(value, str):
                data[field_name] = value.strip()
        milestone_details = []
        amount_values = self.request.POST.getlist("milestone_amounts[]")
        due_dates = self.request.POST.getlist("milestone_due_dates[]")
        conditions = self.request.POST.getlist("milestone_conditions[]")
        for raw_amount, due_date, condition in zip_longest(amount_values, due_dates, conditions, fillvalue=""):
            try:
                amount_value = int(raw_amount) if raw_amount not in (None, "") else 0
            except (TypeError, ValueError):
                amount_value = 0
            amount_value = max(amount_value, 0)
            cleaned_condition = (condition or "").strip()
            due_date_value = (due_date or "").strip()
            if amount_value <= 0 and not due_date_value and not cleaned_condition:
                continue
            milestone_details.append(
                {
                    "amount_sats": amount_value,
                    "due_date": due_date_value,
                    "condition": cleaned_condition,
                }
            )
        data["milestones"] = milestone_details
        data["generated_at"] = timezone.now().isoformat()
        role_display = dict(form.fields["role"].choices).get(data.get("role"), "-")
        payment_display = dict(form.fields["payment_type"].choices).get(data.get("payment_type"), "-")
        data["role_display"] = role_display
        data["payment_display"] = payment_display
        if self.active_contract_template:
            data["contract_template"] = {
                "title": self.active_contract_template.title,
                "version": self.active_contract_template.version_label,
                "content": self.active_contract_template.content,
                "content_html": self.active_contract_template_html,
            }
        return data


class DirectContractReviewView(LoginRequiredMixin, FormView):
    """계약 생성자가 최종 검토 및 서명을 수행하는 화면."""

    template_name = "expert/contract_review.html"
    form_class = ContractReviewForm
    login_url = reverse_lazy("expert:login")
    session_prefix = DirectContractDraftView.session_prefix

    def dispatch(self, request, *args, **kwargs):
        self.token = kwargs.get("token")
        self.session_key = f"{self.session_prefix}:{self.token}"
        self.draft_payload = self.request.session.get(self.session_key)
        if not self.draft_payload:
            messages.warning(request, "검토할 계약 초안이 없습니다. 처음부터 다시 작성해 주세요.")
            return redirect("expert:direct-draft")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        work_log_markdown = (self.draft_payload or {}).get("work_log_markdown", "")
        context.update(
            {
                "draft_payload": self.draft_payload,
                "contract_generated_at": timezone.now(),
                "work_log_html": render_contract_markdown(work_log_markdown),
            }
        )
        return context

    def form_valid(self, form):
        payload = self.draft_payload.copy()
        slug = self._generate_unique_slug()
        creator_role = payload.get("role", "client")
        counterparty_role = "performer" if creator_role == "client" else "client"
        document = DirectContractDocument(
            slug=slug,
            creator=self.request.user,
            payload=payload,
            creator_role=creator_role,
            counterparty_role=counterparty_role,
            creator_email=payload.get("email_recipient") or "",
        )
        creator_hash = build_creator_hash(payload, self.request.META.get("HTTP_USER_AGENT", ""))
        document.creator_hash = creator_hash.value
        document.creator_hash_meta = creator_hash.meta
        document.creator_signed_at = timezone.now()
        document.status = "pending_counterparty"
        document.save()
        record_stage_log("draft", document=document, token=self.token, meta={"title": payload.get("title")})
        record_stage_log("role_one", document=document, meta={"role": creator_role})

        asset, error, signature_file = store_signature_asset_from_data(
            form.cleaned_data["signature_data"], f"creator-{self.request.user.pk}"
        )
        if asset:
            document.set_signature_asset("creator", asset)
            document.clear_signature_file("creator")
        else:
            if not signature_media_fallback_enabled():
                document.delete()
                form.add_error(None, error or "서명 이미지를 저장하지 못했습니다. 잠시 후 다시 시도해주세요.")
                return self.form_invalid(form)
            document.creator_signature.save(signature_file.name, signature_file)
            messages.warning(
                self.request,
                "객체 스토리지 연결을 확인할 수 없어 임시로 로컬 저장소에 서명을 보관했습니다.",
            )
        self.request.session.pop(self.session_key, None)
        self.request.session.modified = True
        return redirect(f"{document.get_absolute_url()}?owner=1")

    def _generate_unique_slug(self) -> str:
        while True:
            slug = generate_share_slug()
            if not DirectContractDocument.objects.filter(slug=slug).exists():
                return slug


class DirectContractInviteView(FormView):
    """생성된 계약을 공유 주소에서 확인/서명하는 화면."""

    template_name = "expert/contract_invite.html"
    form_class = CounterpartySignatureForm

    def dispatch(self, request, *args, **kwargs):
        self.document = get_object_or_404(DirectContractDocument, slug=kwargs.get("slug"))
        self.payload = self.document.payload or {}
        self.is_owner = request.user.is_authenticated and request.user == self.document.creator
        email_delivery = self.document.email_delivery or {}
        for key in ("creator", "counterparty"):
            email_delivery.setdefault(key, {"email": "", "sent": False, "message": ""})
        if email_delivery != self.document.email_delivery:
            self.document.email_delivery = email_delivery
            self.document.save(update_fields=["email_delivery"])
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        if not self._can_accept_submission():
            return None
        return super().get_form(form_class)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["require_performer_lightning"] = self.document.counterparty_role == "performer"
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        is_owner = self.request.user.is_authenticated and self.request.user == self.document.creator
        role_labels = dict(ContractParticipant.ROLE_CHOICES)
        creator_role_label = role_labels.get(self.document.creator_role, "계약 생성자")
        counterparty_role_label = role_labels.get(self.document.counterparty_role, "상대방")
        context.update(
            {
                "document": self.document,
                "payload": self.payload,
                "is_owner": is_owner,
                "waiting_message": self.document.status != "completed" and not self.document.counterparty_signed_at,
                "contract_template": (self.payload.get("contract_template") or {}),
                "share_url": self.request.build_absolute_uri(self.document.get_absolute_url()),
                "signature_assets": {
                    "creator": self.document.get_signature_asset("creator"),
                    "counterparty": self.document.get_signature_asset("counterparty"),
                },
                "creator_signature_url": self.document.get_signature_url("creator")
                or (self.document.creator_signature.url if self.document.creator_signature else ""),
                "counterparty_signature_url": self.document.get_signature_url("counterparty")
                or (self.document.counterparty_signature.url if self.document.counterparty_signature else ""),
                "work_log_html": render_contract_markdown((self.payload or {}).get("work_log_markdown", "")),
                "require_performer_lightning": self.document.counterparty_role == "performer",
                "creator_role_label": creator_role_label,
                "counterparty_role_label": counterparty_role_label,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        if not self._can_accept_submission():
            return redirect(self.document.get_absolute_url())
        return super().post(request, *args, **kwargs)

    def _can_accept_submission(self) -> bool:
        if not hasattr(self, "document"):
            return False
        if self.document.status == "completed":
            return False
        if getattr(self, "is_owner", False):
            return False
        return True

    def form_valid(self, form):
        if self.document.status == "completed":
            return redirect(self.document.get_absolute_url())
        asset, error, signature_file = store_signature_asset_from_data(
            form.cleaned_data["signature_data"], f"counterparty-{self.document.slug}"
        )
        if not asset and not signature_media_fallback_enabled():
            form.add_error(None, error or "서명 이미지를 저장하지 못했습니다. 잠시 후 다시 시도해주세요.")
            return self.form_invalid(form)

        self.document.counterparty_email = form.cleaned_data["email"]
        if self.document.counterparty_role == "performer":
            performer_lightning = form.cleaned_data.get("performer_lightning_address")
            if performer_lightning:
                self.payload["performer_lightning_address"] = performer_lightning
        counterparty_hash = build_counterparty_hash(
            self.document.creator_hash, self.request.META.get("HTTP_USER_AGENT", "")
        )
        self.document.counterparty_hash = counterparty_hash.value
        self.document.counterparty_hash_meta = counterparty_hash.meta
        self.document.counterparty_signed_at = timezone.now()
        self.document.status = "counterparty_in_progress"
        self.document.payload = self.payload
        self.document.save()
        record_stage_log(
            "role_two",
            document=self.document,
            meta={"role": self.document.counterparty_role, "email": self.document.counterparty_email},
        )
        if asset:
            self.document.set_signature_asset("counterparty", asset)
            self.document.clear_signature_file("counterparty")
        else:
            self.document.counterparty_signature.save(signature_file.name, signature_file)
            messages.warning(
                self.request,
                "객체 스토리지 연결을 확인할 수 없어 임시로 로컬 저장소에 서명을 보관했습니다.",
            )

        template_markdown = (
            (self.payload.get("contract_template") or {}).get("content") or ""
        )
        pdf_content = render_contract_pdf(self.document, template_markdown)
        self.document.final_pdf.save(pdf_content.name, pdf_content)
        mediator_hash = build_mediator_hash(self.document.counterparty_hash)
        self.document.mediator_hash = mediator_hash.value
        self.document.mediator_hash_meta = mediator_hash.meta
        self.document.final_pdf_generated_at = timezone.now()
        self.document.status = "completed"
        self.document.save()
        record_stage_log("completed", document=self.document)

        delivery = send_direct_contract_document_email(self.document)
        self.document.email_delivery = delivery
        self.document.save(update_fields=["email_delivery", "updated_at"])
        return redirect(self.document.get_absolute_url())


class DirectContractLibraryView(LoginRequiredMixin, TemplateView):
    """내가 생성한 직접 계약 리스트."""

    template_name = "expert/contract_library.html"
    login_url = reverse_lazy("expert:login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        documents = DirectContractDocument.objects.filter(creator=self.request.user)
        context["documents"] = documents
        return context


class ContractDetailView(LoginRequiredMixin, TemplateView):
    """계약서 상세/채팅 화면."""

    template_name = "expert/contract_detail.html"
    login_url = reverse_lazy("expert:login")

    def dispatch(self, request, *args, **kwargs):
        public_id = kwargs.get("public_id")
        self.contract = get_object_or_404(
            Contract.objects.prefetch_related("participants__user", "messages__sender"),
            public_id=public_id,
        )

        if not (request.user.is_staff or self.contract.participants.filter(user=request.user).exists()):
            return HttpResponseForbidden("이 계약에 접근할 권한이 없습니다.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        messages = self.contract.messages.select_related("sender").order_by("-created_at")[:100]
        context.update(
            {
                "contract": self.contract,
                "messages": reversed(list(messages)),
                "websocket_path": f"/ws/expert/contracts/{self.contract.public_id}/chat/",
            }
        )
        return context


class ExpertLightningLoginGuideView(TemplateView):
    """Expert 전용 라이트닝 로그인 안내 페이지."""

    template_name = "expert/login_lightning.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        default_target = reverse("expert:create-direct")
        redirect_target = self.request.GET.get("next") or default_target
        query_string = urlencode({"next": redirect_target})
        context.update(
            {
                "redirect_target": redirect_target,
                "lightning_login_url": f"{reverse('accounts:lightning_login')}?{query_string}",
                "standard_login_url": f"{reverse('accounts:login')}?{query_string}",
            }
        )
        return context
