from typing import Optional

from django.conf import settings
from django.http import HttpResponse

from .models import normalize_domain
from .services import resolve_minihome_slug_by_domain
from .views import (
    minihome_landing,
    minihome_list,
    minihome_manage,
    minihome_preview,
)


def _resolve_minihome_slug_by_host(host: str) -> Optional[str]:
    domain = normalize_domain(host)
    if not domain:
        return None
    return resolve_minihome_slug_by_domain(domain)


def _is_minihome_list_domain(host: str) -> bool:
    domain = normalize_domain(host)
    list_domain = normalize_domain(settings.MINIHOME_LIST_DOMAIN)
    if not domain or not list_domain:
        return False
    return domain == list_domain


class MinihomeDomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request) -> HttpResponse:
        host = request.get_host().split(":")[0]
        if _is_minihome_list_domain(host):
            path = request.path.strip("/")
            if path == "":
                return minihome_list(request)
            parts = path.split("/")
            slug = parts[0]
            if len(parts) == 1:
                return minihome_landing(request, slug=slug)
            if len(parts) >= 2:
                if parts[1] in ("mng", "mng/"):
                    return minihome_manage(request, slug=slug)
                if parts[1] in ("preview", "preview/"):
                    return minihome_preview(request, slug=slug)
            return self.get_response(request)
        slug = _resolve_minihome_slug_by_host(host)
        if not slug:
            return self.get_response(request)

        path = request.path.strip("/")
        if path == "":
            return minihome_landing(request, slug=slug)
        if path in ("mng", "mng/"):
            return minihome_manage(request, slug=slug)
        if path in ("preview", "preview/"):
            return minihome_preview(request, slug=slug)

        return self.get_response(request)
