from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.http import urlencode
from django.views.generic import TemplateView, FormView

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
