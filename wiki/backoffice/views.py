from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from wiki.forms import WikiEntryForm
from wiki.models import WikiEntry


class WikiPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = "wiki.manage_wiki"
    raise_exception = True
    login_url = reverse_lazy("accounts:login")


class WikiEntryListView(WikiPermissionMixin, ListView):
    template_name = "wiki/backoffice/entry_list.html"
    model = WikiEntry
    context_object_name = "entries"

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get("q")
        if search:
            queryset = queryset.filter(title__icontains=search)
        return queryset.select_related("created_by", "updated_by")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        return context


class WikiEntryCreateView(WikiPermissionMixin, CreateView):
    template_name = "wiki/backoffice/entry_form.html"
    form_class = WikiEntryForm
    success_url = reverse_lazy("wiki_backoffice:entry_list")

    def form_valid(self, form: WikiEntryForm) -> HttpResponseRedirect:
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "위키 항목이 생성되었습니다.")
        return response

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["page_title"] = "위키 항목 추가"
        return context


class WikiEntryUpdateView(WikiPermissionMixin, UpdateView):
    template_name = "wiki/backoffice/entry_form.html"
    form_class = WikiEntryForm
    model = WikiEntry
    success_url = reverse_lazy("wiki_backoffice:entry_list")

    def form_valid(self, form: WikiEntryForm) -> HttpResponseRedirect:
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "위키 항목이 수정되었습니다.")
        return response

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["page_title"] = "위키 항목 수정"
        return context
