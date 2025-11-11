import markdown

import json
import uuid
from datetime import timedelta
from itertools import zip_longest

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import Http404, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import urlencode
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import TemplateView, FormView, RedirectView

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
from .constants import DIRECT_CONTRACT_SESSION_PREFIX, ROLE_LABELS
from .forms import (
    ContractDraftForm,
    ContractIntegrityCheckForm,
    ContractReviewForm,
    CounterpartySignatureForm,
)
from .signature_assets import signature_media_fallback_enabled, store_signature_asset_from_data
from .payment_service import (
    PAYMENT_EXPIRE_SECONDS,
    ExpertPaymentConfigurationError,
    PaymentState,
    build_widget_context,
    clear_payment_state,
    ensure_draft_payload,
    get_blink_service,
    get_payment_state,
    mark_payment_paid,
    store_payment_state,
)
from .utils import (
    PDFSigningError,
    calculate_sha256_from_fileobj,
    pdf_signing_enabled,
    sign_contract_pdf,
)


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


class ExpertLandingView(RedirectView):
    """Expert 기본 경로를 직접 계약 생성 페이지로 리디렉션."""

    permanent = False

    def get_redirect_url(self, *args, **kwargs):  # noqa: D401 - RedirectView 구현 디테일
        return reverse("expert:create-direct")


class LightningLoginRequiredMixin(LoginRequiredMixin):
    """Ensure users completed Lightning login."""

    login_url = reverse_lazy("expert:login")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not _has_lightning_profile(request.user):
            messages.warning(request, "라이트닝 로그인 후 이용할 수 있습니다.")
            login_url = reverse("expert:login")
            query = urlencode({"next": request.get_full_path()})
            return redirect(f"{login_url}?{query}")
        return super().dispatch(request, *args, **kwargs)


def _has_lightning_profile(user) -> bool:
    return user.is_authenticated and getattr(user, "lightning_profile", None) is not None


def _get_lightning_public_key(user) -> str:
    if not user.is_authenticated:
        return ""
    profile = getattr(user, "lightning_profile", None)
    return profile.public_key if profile else ""


def _get_accessible_documents(user):
    lightning_id = _get_lightning_public_key(user)
    query = Q(creator=user) | Q(counterparty_user=user)
    if lightning_id:
        query |= Q(counterparty_signed_at__isnull=False, payload__counterparty_lightning_id=lightning_id)
    return DirectContractDocument.objects.filter(query).order_by("-created_at")


class DirectContractStartView(LightningLoginRequiredMixin, TemplateView):
    """직접 계약 생성 시작 화면 (TODO: 계약 생성 플로우 연결)."""

    template_name = "expert/direct_contract_start.html"
    login_url = reverse_lazy("expert:login")


class DirectContractDraftView(LightningLoginRequiredMixin, FormView):
    """직접 계약 생성 폼 뷰(1차 초안)."""

    template_name = "expert/contract_draft.html"
    form_class = ContractDraftForm
    success_url = reverse_lazy("expert:direct-draft")
    login_url = reverse_lazy("expert:login")
    session_prefix = DIRECT_CONTRACT_SESSION_PREFIX

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
            meta={
                "title": draft_payload.get("title", ""),
                "payment_type": draft_payload.get("payment_type"),
                "lightning_id": _get_lightning_public_key(self.request.user),
            },
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


class DirectContractReviewView(LightningLoginRequiredMixin, FormView):
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
        self.creator_role = self.draft_payload.get("role", "client")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        work_log_markdown = (self.draft_payload or {}).get("work_log_markdown", "")
        payment_widget = build_widget_context(
            self.request,
            context_type="draft",
            identifier=self.token,
            role=self.creator_role,
            role_label=ROLE_LABELS.get(self.creator_role, self.creator_role),
        )
        context.update(
            {
                "draft_payload": self.draft_payload,
                "contract_generated_at": timezone.now(),
                "work_log_html": render_contract_markdown(work_log_markdown),
                "payment_widget": payment_widget,
                "payment_expire_seconds": PAYMENT_EXPIRE_SECONDS,
                "creator_lightning_id": _get_lightning_public_key(self.request.user),
                "counterparty_lightning_id": self.draft_payload.get("counterparty_lightning_id", ""),
            }
        )
        return context

    def form_valid(self, form):
        payment_widget = build_widget_context(
            self.request,
            context_type="draft",
            identifier=self.token,
            role=self.creator_role,
            role_label=ROLE_LABELS.get(self.creator_role, self.creator_role),
        )
        if payment_widget.requires_payment and payment_widget.state.status != "paid":
            form.add_error(None, "라이트닝 결제를 완료한 뒤 계약서 주소를 생성할 수 있습니다.")
            return self.form_invalid(form)
        payment_receipt = self._build_payment_receipt(payment_widget)
        payload = self.draft_payload.copy()
        creator_lightning_id = _get_lightning_public_key(self.request.user)
        if creator_lightning_id:
            payload["creator_lightning_id"] = creator_lightning_id
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
        record_stage_log(
            "draft",
            document=document,
            token=self.token,
            meta={
                "title": payload.get("title"),
                "payment_type": payload.get("payment_type"),
                "lightning_id": creator_lightning_id,
            },
        )
        self._ensure_draft_log_attached(document)

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
        self._persist_creator_payment(document, payment_receipt)
        record_stage_log(
            "role_one",
            document=document,
            meta={
                "role": creator_role,
                "signed_at": timezone.localtime(document.creator_signed_at).isoformat() if document.creator_signed_at else "",
                "lightning_id": creator_lightning_id,
            },
        )
        clear_payment_state(self.request, "draft", self.token, creator_role)
        return redirect(f"{document.get_absolute_url()}?owner=1")

    def _generate_unique_slug(self) -> str:
        while True:
            slug = generate_share_slug()
            if not DirectContractDocument.objects.filter(slug=slug).exists():
                return slug

    def _persist_creator_payment(self, document: DirectContractDocument, receipt: dict | None = None):
        stage_log = (
            DirectContractStageLog.objects.filter(stage="draft", document=document)
            .order_by("started_at")
            .first()
        )
        payment_receipt = None
        if stage_log:
            meta = stage_log.meta or {}
            payment_receipt = meta.get("payment")
            if receipt and not payment_receipt:
                meta["payment"] = receipt
                stage_log.meta = meta
                stage_log.save(update_fields=["meta"])
                payment_receipt = receipt
        if not payment_receipt:
            payment_receipt = receipt
        if not payment_receipt:
            return
        payment_meta = document.payment_meta or {}
        if payment_meta.get(document.creator_role) == payment_receipt:
            return
        payment_meta[document.creator_role] = payment_receipt
        document.payment_meta = payment_meta
        document.save(update_fields=["payment_meta", "updated_at"])

    def _ensure_draft_log_attached(self, document: DirectContractDocument):
        DirectContractStageLog.objects.filter(stage="draft", token=self.token or "", document__isnull=True).update(
            document=document
        )

    def _build_payment_receipt(self, payment_widget) -> dict | None:
        state = payment_widget.state
        if state.status != "paid":
            return None
        paid_at = state.paid_at or timezone.now()
        if timezone.is_naive(paid_at):
            paid_at = timezone.make_aware(paid_at, timezone=timezone.utc)
        return {
            "amount_sats": state.amount_sats,
            "paid_at": paid_at.isoformat(),
            "payment_hash": state.payment_hash,
            "payment_request": state.payment_request,
        }


class DirectContractInviteView(LightningLoginRequiredMixin, FormView):
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
        creator_lightning_id = (self.payload or {}).get("creator_lightning_id") or _get_lightning_public_key(
            self.document.creator
        )
        counterparty_payload_lightning = (self.payload or {}).get("counterparty_lightning_id", "")
        viewer_lightning_id = _get_lightning_public_key(self.request.user)
        template_data = (self.payload.get("contract_template") or {}).copy()
        template_content = template_data.get("content", "")
        if template_content and not template_data.get("content_html"):
            template_data["content_html"] = render_contract_markdown(template_content)
        if not template_data.get("content_html"):
            fallback_template = ContractTemplate.objects.filter(is_selected=True).first()
            if fallback_template:
                template_data = {
                    "title": template_data.get("title") or fallback_template.title,
                    "version": template_data.get("version") or fallback_template.version_label,
                    "content": template_content or fallback_template.content,
                    "content_html": render_contract_markdown(fallback_template.content),
                }

        context.update(
            {
                "document": self.document,
                "payload": self.payload,
                "is_owner": is_owner,
                "waiting_message": self.document.status != "completed" and not self.document.counterparty_signed_at,
                "contract_template": template_data,
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
                "creator_lightning_id": creator_lightning_id,
                "counterparty_lightning_id": counterparty_payload_lightning,
                "viewer_lightning_id": viewer_lightning_id,
            }
        )
        form_instance = context.get("form")
        if form_instance:
            payment_widget = build_widget_context(
                self.request,
                context_type="invite",
                identifier=self.document.slug,
                role=self.document.counterparty_role,
                role_label=counterparty_role_label,
            )
            context["payment_widget"] = payment_widget
            context["payment_expire_seconds"] = PAYMENT_EXPIRE_SECONDS
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
        payment_widget = build_widget_context(
            self.request,
            context_type="invite",
            identifier=self.document.slug,
            role=self.document.counterparty_role,
            role_label=dict(ContractParticipant.ROLE_CHOICES).get(
                self.document.counterparty_role,
                "상대방",
            ),
        )
        if payment_widget.requires_payment and payment_widget.state.status != "paid":
            form.add_error(None, "라이트닝 결제를 완료한 뒤 서명해주세요.")
            return self.form_invalid(form)
        asset, error, signature_file = store_signature_asset_from_data(
            form.cleaned_data["signature_data"], f"counterparty-{self.document.slug}"
        )
        if not asset and not signature_media_fallback_enabled():
            form.add_error(None, error or "서명 이미지를 저장하지 못했습니다. 잠시 후 다시 시도해주세요.")
            return self.form_invalid(form)

        self.document.counterparty_email = form.cleaned_data["email"]
        self.document.counterparty_user = self.request.user
        counterparty_lightning_id = _get_lightning_public_key(self.request.user)
        if counterparty_lightning_id:
            self.payload["counterparty_lightning_id"] = counterparty_lightning_id
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
        payment_receipt = (self.document.payment_meta or {}).get(self.document.counterparty_role)
        stage_meta = {
            "role": self.document.counterparty_role,
            "email": self.document.counterparty_email,
            "lightning_id": counterparty_lightning_id,
        }
        if payment_receipt:
            stage_meta["payment"] = payment_receipt
        if asset:
            self.document.set_signature_asset("counterparty", asset)
            self.document.clear_signature_file("counterparty")
        else:
            self.document.counterparty_signature.save(signature_file.name, signature_file)
            messages.warning(
                self.request,
                "객체 스토리지 연결을 확인할 수 없어 임시로 로컬 저장소에 서명을 보관했습니다.",
            )

        if self.document.counterparty_signed_at:
            stage_meta["signed_at"] = timezone.localtime(self.document.counterparty_signed_at).isoformat()
        record_stage_log("role_two", document=self.document, meta=stage_meta)

        mediator_hash = build_mediator_hash(self.document.counterparty_hash)
        self.document.mediator_hash = mediator_hash.value
        self.document.mediator_hash_meta = mediator_hash.meta
        template_markdown = (
            (self.payload.get("contract_template") or {}).get("content") or ""
        )
        pdf_content = render_contract_pdf(self.document, template_markdown)
        try:
            pdf_content = sign_contract_pdf(pdf_content)
        except PDFSigningError as exc:
            pdf_content.seek(0)
            messages.warning(
                self.request,
                f"전자 서명에 실패해 서명 없이 계약서를 저장했습니다. (사유: {exc})",
            )
        pdf_hash = calculate_sha256_from_fileobj(pdf_content)
        self.document.final_pdf.save(pdf_content.name, pdf_content)
        self.document.final_pdf_hash = pdf_hash
        self.document.final_pdf_generated_at = timezone.now()
        self.document.status = "completed"
        self.document.save()
        record_stage_log("completed", document=self.document)

        delivery = send_direct_contract_document_email(self.document)
        self.document.email_delivery = delivery
        self.document.save(update_fields=["email_delivery", "updated_at"])
        clear_payment_state(self.request, "invite", self.document.slug, self.document.counterparty_role)
        return redirect(self.document.get_absolute_url())


class DirectContractLibraryView(LightningLoginRequiredMixin, TemplateView):
    """생성했거나 서명한 직접 계약 리스트."""

    template_name = "expert/contract_library.html"
    login_url = reverse_lazy("expert:login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        documents = _get_accessible_documents(self.request.user)
        context["documents"] = documents
        return context


class DirectContractIntegrityCheckView(LightningLoginRequiredMixin, FormView):
    """업로드한 PDF와 원본 해시를 비교하는 검증 도구."""

    template_name = "expert/contract_integrity_check.html"
    form_class = ContractIntegrityCheckForm
    login_url = reverse_lazy("expert:login")

    def dispatch(self, request, *args, **kwargs):
        self.documents = list(_get_accessible_documents(request.user))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["documents"] = self.documents
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "documents": self.documents,
                "documents_count": len(self.documents),
                "pdf_signing_enabled": pdf_signing_enabled(),
            }
        )
        if not self.documents:
            context["empty_message"] = "계약을 먼저 생성하거나 서명 완료해야 검증 도구를 이용할 수 있습니다."
        return context

    def form_valid(self, form):
        document = form.get_document()
        uploaded_file = form.cleaned_data["pdf_file"]
        uploaded_hash = calculate_sha256_from_fileobj(uploaded_file)
        stored_hash = document.final_pdf_hash or ""
        if not stored_hash:
            status = "pending"
            message = "이 계약서는 아직 해시가 저장되지 않았습니다. 계약을 다시 완료하거나 관리자에게 문의하세요."
        elif stored_hash == uploaded_hash:
            status = "match"
            message = "업로드한 PDF가 원본과 일치합니다."
        else:
            status = "mismatch"
            message = "해시가 일치하지 않습니다. 위변조 가능성이 있으니 원본 계약서를 다시 내려받아 공유하세요."
        context = self.get_context_data(form=form)
        context["result"] = {
            "status": status,
            "message": message,
            "uploaded_hash": uploaded_hash,
            "stored_hash": stored_hash,
            "document": document,
        }
        return self.render_to_response(context)


class ContractDetailView(LightningLoginRequiredMixin, TemplateView):
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


class PaymentAccessError(Exception):
    """지불 위젯 요청 검증 중 발생하는 에러."""

    def __init__(self, message: str, *, status: int = 400):
        super().__init__(message)
        self.status = status


def _parse_payment_payload(data) -> tuple[str, str, str]:
    context_type = (data.get("context") or "").strip()
    identifier = (data.get("ref") or "").strip()
    role = (data.get("role") or "").strip()
    if context_type not in {"draft", "invite"}:
        raise ValueError("context")
    if not identifier:
        raise ValueError("ref")
    if role not in ROLE_LABELS:
        raise ValueError("role")
    return context_type, identifier, role


def _ensure_payment_role(request, context_type: str, identifier: str, role: str) -> str:
    if context_type == "draft":
        if not request.user.is_authenticated:
            raise PaymentAccessError("로그인이 필요합니다.", status=403)
        payload = ensure_draft_payload(request, identifier)
        if not payload:
            raise Http404("draft payload not found")
        if payload.get("role") != role:
            raise PaymentAccessError("역할 정보가 일치하지 않습니다.")
        return ROLE_LABELS.get(role, role)

    document = get_object_or_404(DirectContractDocument, slug=identifier)
    if document.counterparty_role != role:
        raise PaymentAccessError("역할 정보가 일치하지 않습니다.")
    if document.status == "completed":
        raise PaymentAccessError("이미 완료된 계약입니다.")
    return ROLE_LABELS.get(role, role)


def _render_payment_widget(request, context_type: str, identifier: str, role: str, role_label: str):
    widget = build_widget_context(
        request,
        context_type=context_type,
        identifier=identifier,
        role=role,
        role_label=role_label,
    )
    return render(
        request,
        "expert/partials/lightning_payment_box.html",
        {"payment_widget": widget, "payment_expire_seconds": PAYMENT_EXPIRE_SECONDS},
    )


def _build_invoice_memo(context_type: str, identifier: str, role_label: str) -> str:
    prefix = getattr(settings, "EXPERT_BLINK_MEMO_PREFIX", "SatoShop Expert 결제")
    descriptor = "검토" if context_type == "draft" else "공유"
    short_ref = identifier[:10]
    return f"{prefix} · {role_label} {descriptor} · {short_ref}"


@require_http_methods(["GET"])
def direct_contract_payment_widget(request):
    try:
        context_type, identifier, role = _parse_payment_payload(request.GET)
    except ValueError:
        return HttpResponseBadRequest("잘못된 요청입니다.")
    try:
        role_label = _ensure_payment_role(request, context_type, identifier, role)
    except PaymentAccessError as exc:
        if exc.status == 403:
            return HttpResponseForbidden(str(exc))
        return HttpResponseBadRequest(str(exc))
    return _render_payment_widget(request, context_type, identifier, role, role_label)


@require_POST
def direct_contract_payment_start(request):
    try:
        context_type, identifier, role = _parse_payment_payload(request.POST)
    except ValueError:
        return HttpResponseBadRequest("잘못된 요청입니다.")
    try:
        role_label = _ensure_payment_role(request, context_type, identifier, role)
    except PaymentAccessError as exc:
        if exc.status == 403:
            return HttpResponseForbidden(str(exc))
        return HttpResponseBadRequest(str(exc))

    widget = build_widget_context(
        request,
        context_type=context_type,
        identifier=identifier,
        role=role,
        role_label=role_label,
    )
    if not widget.requires_payment:
        return _render_payment_widget(request, context_type, identifier, role, role_label)

    try:
        blink_service = get_blink_service()
        memo = _build_invoice_memo(context_type, identifier, role_label)
        blink_response = blink_service.create_invoice(
            amount_sats=widget.required_amount,
            memo=memo,
            expires_in_minutes=max(1, PAYMENT_EXPIRE_SECONDS // 60 or 1),
        )
    except ExpertPaymentConfigurationError as exc:
        state = PaymentState(
            status="error",
            amount_sats=widget.required_amount,
            last_error=str(exc),
            message=str(exc),
        )
        store_payment_state(request, context_type, identifier, role, state)
        return _render_payment_widget(request, context_type, identifier, role, role_label)
    except Exception as exc:  # noqa: BLE001
        state = PaymentState(
            status="error",
            amount_sats=widget.required_amount,
            last_error=str(exc),
            message="인보이스를 생성하지 못했습니다. 잠시 후 다시 시도해주세요.",
        )
        store_payment_state(request, context_type, identifier, role, state)
        return _render_payment_widget(request, context_type, identifier, role, role_label)

    if not blink_response.get("success"):
        state = PaymentState(
            status="error",
            amount_sats=widget.required_amount,
            last_error=blink_response.get("error", "인보이스 생성에 실패했습니다."),
            message="인보이스 생성 중 오류가 발생했습니다.",
        )
        store_payment_state(request, context_type, identifier, role, state)
        return _render_payment_widget(request, context_type, identifier, role, role_label)

    expires_at = timezone.now() + timedelta(seconds=PAYMENT_EXPIRE_SECONDS)
    blink_expires = blink_response.get("expires_at")
    if blink_expires:
        if timezone.is_naive(blink_expires):
            blink_expires = timezone.make_aware(blink_expires, timezone=timezone.utc)
        expires_at = min(expires_at, blink_expires)
    state = PaymentState(
        status="invoice",
        amount_sats=widget.required_amount,
        payment_hash=blink_response.get("payment_hash", ""),
        payment_request=blink_response.get("invoice", ""),
        expires_at=expires_at,
        message="인보이스를 생성했습니다. 60초 이내에 결제를 완료해 주세요.",
    )
    store_payment_state(request, context_type, identifier, role, state)
    return _render_payment_widget(request, context_type, identifier, role, role_label)


@require_POST
def direct_contract_payment_cancel(request):
    try:
        context_type, identifier, role = _parse_payment_payload(request.POST)
    except ValueError:
        return HttpResponseBadRequest("잘못된 요청입니다.")
    try:
        role_label = _ensure_payment_role(request, context_type, identifier, role)
    except PaymentAccessError as exc:
        if exc.status == 403:
            return HttpResponseForbidden(str(exc))
        return HttpResponseBadRequest(str(exc))

    state = get_payment_state(request, context_type, identifier, role)
    state.status = "cancelled"
    state.payment_hash = ""
    state.payment_request = ""
    state.expires_at = None
    state.message = "인보이스를 취소했습니다."
    store_payment_state(request, context_type, identifier, role, state)
    return _render_payment_widget(request, context_type, identifier, role, role_label)


@require_POST
def direct_contract_payment_status(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "잘못된 요청입니다."}, status=400)
    try:
        context_type, identifier, role = _parse_payment_payload(payload)
    except ValueError:
        return JsonResponse({"ok": False, "error": "잘못된 요청입니다."}, status=400)
    try:
        role_label = _ensure_payment_role(request, context_type, identifier, role)
    except PaymentAccessError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=exc.status)

    widget = build_widget_context(
        request,
        context_type=context_type,
        identifier=identifier,
        role=role,
        role_label=role_label,
    )
    state = widget.state
    if not widget.requires_payment:
        mark_payment_paid(request, context_type, identifier, role)
        return JsonResponse({"ok": True, "status": "skipped", "message": widget.status_message})

    if state.status == "paid":
        return JsonResponse({"ok": True, "status": "paid", "message": widget.status_message})

    if not state.payment_hash:
        return JsonResponse({"ok": False, "error": "활성화된 인보이스가 없습니다."}, status=400)

    if state.expires_at and timezone.now() >= state.expires_at:
        state.status = "expired"
        state.payment_hash = ""
        state.payment_request = ""
        state.message = "인보이스가 만료되었습니다. 다시 생성해 주세요."
        store_payment_state(request, context_type, identifier, role, state)
        return JsonResponse({"ok": True, "status": "expired", "message": state.message})

    try:
        blink_service = get_blink_service()
        result = blink_service.check_invoice_status(state.payment_hash)
    except ExpertPaymentConfigurationError as exc:
        state.status = "error"
        state.last_error = str(exc)
        state.message = str(exc)
        store_payment_state(request, context_type, identifier, role, state)
        return JsonResponse({"ok": False, "status": "error", "error": str(exc)}, status=500)
    except Exception as exc:  # noqa: BLE001
        state.status = "error"
        state.last_error = str(exc)
        state.message = "결제 상태를 확인하지 못했습니다."
        store_payment_state(request, context_type, identifier, role, state)
        return JsonResponse({"ok": False, "status": "error", "error": state.message}, status=500)

    if not result.get("success"):
        state.status = "error"
        state.last_error = result.get("error", "결제 상태를 확인하지 못했습니다.")
        state.message = state.last_error
        store_payment_state(request, context_type, identifier, role, state)
        return JsonResponse({"ok": False, "status": "error", "error": state.last_error}, status=500)

    status_value = result.get("status")
    if status_value == "paid":
        mark_payment_paid(request, context_type, identifier, role)
        return JsonResponse({"ok": True, "status": "paid", "message": "결제가 완료되었습니다."})
    if status_value == "expired":
        state.status = "expired"
        state.payment_hash = ""
        state.payment_request = ""
        state.message = "인보이스가 만료되었습니다. 다시 생성해 주세요."
        store_payment_state(request, context_type, identifier, role, state)
        return JsonResponse({"ok": True, "status": "expired", "message": state.message})

    remaining_seconds = widget.countdown_seconds
    state.message = "결제 신호를 확인하는 중입니다."
    store_payment_state(request, context_type, identifier, role, state)
    return JsonResponse(
        {
            "ok": True,
            "status": "pending",
            "message": state.message,
            "remaining_seconds": remaining_seconds,
        }
    )
