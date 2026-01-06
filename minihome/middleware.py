from typing import Optional

from django.http import HttpResponse

from .models import Minihome, normalize_domain
from .views import (
    minihome_landing,
    minihome_manage,
    minihome_preview,
    minihome_add_blog_post,
    minihome_add_gallery_item,
    minihome_add_store_item,
)


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
        if path in ("gallery/add", "gallery/add/"):
            return minihome_add_gallery_item(request, slug=minihome.slug)
        if path in ("blog/add", "blog/add/"):
            return minihome_add_blog_post(request, slug=minihome.slug)
        if path in ("store/add", "store/add/"):
            return minihome_add_store_item(request, slug=minihome.slug)

        return self.get_response(request)
