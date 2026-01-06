from typing import Optional

from django.http import HttpResponse

from .models import normalize_domain
from .services import resolve_minihome_slug_by_domain
from .views import minihome_landing, minihome_manage, minihome_preview


def _resolve_minihome_slug_by_host(host: str) -> Optional[str]:
    domain = normalize_domain(host)
    if not domain:
        return None
    return resolve_minihome_slug_by_domain(domain)


class MinihomeDomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request) -> HttpResponse:
        host = request.get_host().split(":")[0]
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
