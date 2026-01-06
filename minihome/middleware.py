from typing import Optional

from django.http import HttpResponse

from .models import Minihome, normalize_domain
from .views import minihome_landing, minihome_manage, minihome_preview


def _resolve_minihome_by_host(host: str) -> Optional[Minihome]:
    domain = normalize_domain(host)
    if not domain:
        return None
    return Minihome.objects.filter(domain=domain).first()


class MinihomeDomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request) -> HttpResponse:
        host = request.get_host().split(":")[0]
        minihome = _resolve_minihome_by_host(host)
        if not minihome:
            return self.get_response(request)

        path = request.path.strip("/")
        if path == "":
            return minihome_landing(request, slug=minihome.slug)
        if path in ("mng", "mng/"):
            return minihome_manage(request, slug=minihome.slug)
        if path in ("preview", "preview/"):
            return minihome_preview(request, slug=minihome.slug)

        return self.get_response(request)
