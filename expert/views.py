from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.http import urlencode
from django.views import View
from django.views.generic import TemplateView, FormView

from storage.utils import upload_file_to_s3

from .models import Contract, ContractTemplate
from .forms import ContractDraftForm


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        template = ContractTemplate.objects.filter(is_selected=True).first()
        context["active_contract_template"] = template
        if template:
            context["contract_template_payload"] = {
                "title": template.title,
                "version": template.version_label,
                "content": template.content,
            }
        return context

    def form_valid(self, form):
        form.add_error(None, "계약 저장 기능은 준비 중입니다. 입력값을 확인했습니다.")
        return self.form_invalid(form)


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


class ContractAttachmentUploadView(LoginRequiredMixin, View):
    """드래프트 단계에서 PDF 첨부를 S3로 업로드."""

    http_method_names = ["post"]
    upload_prefix = "expert/contracts/attachments"
    allowed_mime_types = {"application/pdf", "application/x-pdf"}

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get("attachment")
        if not file_obj:
            return JsonResponse({"success": False, "error": "업로드할 PDF를 선택해 주세요."}, status=400)

        if not self._is_pdf(file_obj):
            return JsonResponse({"success": False, "error": "PDF 형식의 파일만 업로드할 수 있습니다."}, status=400)

        max_bytes = getattr(settings, "EXPERT_CONTRACT_ATTACHMENT_MAX_BYTES", 5 * 1024 * 1024)
        if file_obj.size > max_bytes:
            human_limit = f"{max_bytes // (1024 * 1024)}MB"
            return JsonResponse(
                {"success": False, "error": f"파일 용량이 허용 범위를 초과했습니다. (최대 {human_limit})"},
                status=400,
            )

        upload_result = upload_file_to_s3(file_obj, prefix=self.upload_prefix)
        if not upload_result.get("success"):
            return JsonResponse(
                {"success": False, "error": upload_result.get("error", "파일 업로드에 실패했습니다.")},
                status=500,
            )

        attachment = {
            "name": upload_result.get("original_name") or file_obj.name,
            "size": upload_result.get("file_size") or file_obj.size,
            "url": upload_result.get("file_url"),
            "path": upload_result.get("file_path"),
            "storage": upload_result.get("storage", "s3"),
        }
        return JsonResponse({"success": True, "attachment": attachment})

    def _is_pdf(self, file_obj):
        if not file_obj:
            return False
        content_type = getattr(file_obj, "content_type", "")
        if content_type in self.allowed_mime_types:
            return True
        return file_obj.name.lower().endswith(".pdf")
