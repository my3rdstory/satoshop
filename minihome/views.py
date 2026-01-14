import json
import uuid
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import Minihome, normalize_domain
from .services import upload_minihome_image


SECTION_TYPES = (
    "brand_image",
    "title",
    "gallery",
    "mini_blog",
    "store",
    "infographic",
    "cta",
    "contributor",
)

BACKGROUND_PRESETS = (
    {"value": "noir", "label": "노아르"},
    {"value": "obsidian", "label": "옵시디언"},
    {"value": "slate", "label": "슬레이트"},
    {"value": "void", "label": "보이드"},
    {"value": "nebula", "label": "네뷸라"},
    {"value": "ember", "label": "엠버"},
    {"value": "aurora", "label": "오로라"},
    {"value": "frost", "label": "프로스트"},
    {"value": "cobalt", "label": "코발트"},
    {"value": "dusk", "label": "더스크"},
    {"value": "graphite", "label": "그래파이트"},
    {"value": "velvet", "label": "벨벳"},
    {"value": "midnight", "label": "미드나이트"},
    {"value": "eclipse", "label": "이클립스"},
    {"value": "forge", "label": "포지"},
    {"value": "horizon", "label": "호라이즌"},
    {"value": "grid", "label": "그리드"},
    {"value": "grain", "label": "그레인"},
    {"value": "basalt", "label": "바솔트"},
    {"value": "ripple", "label": "리플"},
)
DEFAULT_BACKGROUND_PRESET = "noir"
BACKGROUND_PRESET_VALUES = {preset["value"] for preset in BACKGROUND_PRESETS}
BACKGROUND_PRESET_LABELS = {preset["value"]: preset["label"] for preset in BACKGROUND_PRESETS}

BRAND_IMAGE_WIDTH = 900
GALLERY_IMAGE_WIDTH = 900
BLOG_IMAGE_WIDTH = 1000
CTA_PROFILE_MAX_SIZE = (300, 300)
CTA_DONATION_QR_WIDTH = 300
STORE_IMAGE_WIDTH = 600
INFOGRAPHIC_IMAGE_WIDTH = 1000
CONTRIBUTOR_THUMB_SIZE = 100


def _user_can_manage(minihome: Minihome, user) -> bool:
    if not user.is_authenticated:
        return False
    return minihome.owners.filter(pk=user.pk).exists()


def _limit_text(value, limit: int) -> str:
    return (value or "").strip()[:limit]


def _normalize_background_preset(value: str) -> str:
    if value in BACKGROUND_PRESET_VALUES:
        return value
    return DEFAULT_BACKGROUND_PRESET


def _normalize_image_meta(meta):
    if not isinstance(meta, dict):
        return None
    required = {"path", "url", "width", "height"}
    if not required.issubset(meta.keys()):
        return None
    return {
        "path": meta.get("path"),
        "url": meta.get("url"),
        "width": meta.get("width"),
        "height": meta.get("height"),
    }


def _ensure_id(value):
    return value or uuid.uuid4().hex


def _normalize_sections(sections):
    normalized = []
    if not isinstance(sections, list):
        return normalized

    for raw_section in sections:
        if not isinstance(raw_section, dict):
            continue
        section_type = raw_section.get("type")
        if section_type not in SECTION_TYPES:
            continue
        section_id = _ensure_id(raw_section.get("id"))
        data = raw_section.get("data") if isinstance(raw_section.get("data"), dict) else {}

        if section_type == "brand_image":
            image_meta = _normalize_image_meta(data.get("image"))
            normalized.append({
                "id": section_id,
                "type": section_type,
                "data": {"image": image_meta},
            })
            continue

        if section_type == "infographic":
            image_meta = _normalize_image_meta(data.get("image"))
            normalized.append({
                "id": section_id,
                "type": section_type,
                "data": {"image": image_meta},
            })
            continue

        if section_type == "title":
            normalized.append({
                "id": section_id,
                "type": section_type,
                "data": {
                    "title": _limit_text(data.get("title"), 1000),
                    "description": _limit_text(data.get("description"), 10000),
                },
            })
            continue

        if section_type == "gallery":
            items = []
            for item in data.get("items", []):
                if not isinstance(item, dict):
                    continue
                item_id = _ensure_id(item.get("id"))
                items.append({
                    "id": item_id,
                    "description": _limit_text(item.get("description"), 10000),
                    "image": _normalize_image_meta(item.get("image")),
                })
            normalized.append({
                "id": section_id,
                "type": section_type,
                "data": {"items": items},
            })
            continue

        if section_type == "mini_blog":
            posts = []
            for post in data.get("posts", []):
                if not isinstance(post, dict):
                    continue
                post_id = _ensure_id(post.get("id"))
                body = _limit_text(post.get("body") or post.get("text"), 1000)
                title = _limit_text(post.get("title") or body, 100)
                images = post.get("images", [])
                if not isinstance(images, list):
                    images = []
                normalized_images = []
                for image in images[:4]:
                    normalized_images.append(_normalize_image_meta(image))
                while len(normalized_images) < 4:
                    normalized_images.append(None)
                posts.append({
                    "id": post_id,
                    "title": title,
                    "body": body,
                    "images": normalized_images,
                })
            normalized.append({
                "id": section_id,
                "type": section_type,
                "data": {"posts": posts},
            })
            continue

        if section_type == "store":
            stores = []
            for store in data.get("stores", []):
                if not isinstance(store, dict):
                    continue
                store_id = _ensure_id(store.get("id"))
                stores.append({
                    "id": store_id,
                    "name": _limit_text(store.get("name"), 50),
                    "description": _limit_text(store.get("description"), 100),
                    "map_url": _limit_text(store.get("map_url"), 200),
                    "cover_image": _normalize_image_meta(store.get("cover_image")),
                })
            normalized.append({
                "id": section_id,
                "type": section_type,
                "data": {"stores": stores},
            })
            continue

        if section_type == "cta":
            normalized.append({
                "id": section_id,
                "type": section_type,
                "data": {
                    "profile_image": _normalize_image_meta(data.get("profile_image")),
                    "donation_qr": _normalize_image_meta(data.get("donation_qr")),
                    "description": _limit_text(data.get("description"), 200),
                    "email": _limit_text(data.get("email"), 100),
                    "donation": _limit_text(data.get("donation"), 100),
                },
            })
            continue

        if section_type == "contributor":
            contributors = []
            for contributor in data.get("contributors", []):
                if not isinstance(contributor, dict):
                    continue
                contributor_id = _ensure_id(contributor.get("id"))
                contributors.append({
                    "id": contributor_id,
                    "nickname": _limit_text(contributor.get("nickname"), 20),
                    "profile_url": _limit_text(contributor.get("profile_url"), 200),
                    "thumbnail": _normalize_image_meta(contributor.get("thumbnail")),
                })
            normalized.append({
                "id": section_id,
                "type": section_type,
                "data": {"contributors": contributors},
            })

    return normalized


def _apply_uploaded_files(minihome, sections, files):
    section_map = {section["id"]: section for section in sections}
    prefix_base = f"minihome/{minihome.slug}"

    for field_name, file in files.items():
        parts = field_name.split("__")
        if not parts:
            continue

        if parts[0] == "brand_image" and len(parts) == 2:
            section = section_map.get(parts[1])
            if not section:
                continue
            result = upload_minihome_image(
                file,
                prefix=f"{prefix_base}/brand",
                target_width=BRAND_IMAGE_WIDTH,
            )
            if result.get("success"):
                section["data"]["image"] = {
                    "path": result["file_path"],
                    "url": result["file_url"],
                    "width": result["width"],
                    "height": result["height"],
                }

        if parts[0] == "infographic" and len(parts) == 2:
            section = section_map.get(parts[1])
            if not section:
                continue
            result = upload_minihome_image(
                file,
                prefix=f"{prefix_base}/infographic",
                target_width=INFOGRAPHIC_IMAGE_WIDTH,
            )
            if result.get("success"):
                section["data"]["image"] = {
                    "path": result["file_path"],
                    "url": result["file_url"],
                    "width": result["width"],
                    "height": result["height"],
                }

        if parts[0] == "gallery" and len(parts) == 3:
            section = section_map.get(parts[1])
            if not section:
                continue
            for item in section["data"].get("items", []):
                if item.get("id") != parts[2]:
                    continue
                result = upload_minihome_image(
                    file,
                    prefix=f"{prefix_base}/gallery",
                    target_width=GALLERY_IMAGE_WIDTH,
                )
                if result.get("success"):
                    item["image"] = {
                        "path": result["file_path"],
                        "url": result["file_url"],
                        "width": result["width"],
                        "height": result["height"],
                    }

        if parts[0] == "blog" and len(parts) == 4:
            section = section_map.get(parts[1])
            if not section:
                continue
            post_id = parts[2]
            try:
                slot = int(parts[3])
            except ValueError:
                continue
            if slot < 0 or slot > 3:
                continue
            for post in section["data"].get("posts", []):
                if post.get("id") != post_id:
                    continue
                result = upload_minihome_image(
                    file,
                    prefix=f"{prefix_base}/blog",
                    target_width=BLOG_IMAGE_WIDTH,
                )
                if result.get("success"):
                    post["images"][slot] = {
                        "path": result["file_path"],
                        "url": result["file_url"],
                        "width": result["width"],
                        "height": result["height"],
                    }

        if parts[0] == "cta_profile" and len(parts) == 2:
            section = section_map.get(parts[1])
            if not section:
                continue
            result = upload_minihome_image(
                file,
                prefix=f"{prefix_base}/cta",
                max_size=CTA_PROFILE_MAX_SIZE,
            )
            if result.get("success"):
                section["data"]["profile_image"] = {
                    "path": result["file_path"],
                    "url": result["file_url"],
                    "width": result["width"],
                    "height": result["height"],
                }

        if parts[0] == "cta_donation_qr" and len(parts) == 2:
            section = section_map.get(parts[1])
            if not section:
                continue
            result = upload_minihome_image(
                file,
                prefix=f"{prefix_base}/cta",
                target_width=CTA_DONATION_QR_WIDTH,
            )
            if result.get("success"):
                section["data"]["donation_qr"] = {
                    "path": result["file_path"],
                    "url": result["file_url"],
                    "width": result["width"],
                    "height": result["height"],
                }

        if parts[0] == "store" and len(parts) == 3:
            section = section_map.get(parts[1])
            if not section:
                continue
            for store in section["data"].get("stores", []):
                if store.get("id") != parts[2]:
                    continue
                result = upload_minihome_image(
                    file,
                    prefix=f"{prefix_base}/store",
                    target_width=STORE_IMAGE_WIDTH,
                )
                if result.get("success"):
                    store["cover_image"] = {
                        "path": result["file_path"],
                        "url": result["file_url"],
                        "width": result["width"],
                        "height": result["height"],
                    }

        if parts[0] == "contributor" and len(parts) == 3:
            section = section_map.get(parts[1])
            if not section:
                continue
            for contributor in section["data"].get("contributors", []):
                if contributor.get("id") != parts[2]:
                    continue
                result = upload_minihome_image(
                    file,
                    prefix=f"{prefix_base}/contributor",
                    square_size=CONTRIBUTOR_THUMB_SIZE,
                )
                if result.get("success"):
                    contributor["thumbnail"] = {
                        "path": result["file_path"],
                        "url": result["file_url"],
                        "width": result["width"],
                        "height": result["height"],
                    }

    return sections


def minihome_list(request):
    minihomes = Minihome.objects.filter(is_published=True).order_by("-updated_at")
    host = request.get_host().split(":")[0]
    list_domain = normalize_domain(settings.MINIHOME_LIST_DOMAIN)
    is_list_domain = bool(list_domain) and normalize_domain(host) == list_domain
    if list_domain and not is_list_domain:
        query = request.GET.urlencode()
        target = f"{request.scheme}://{list_domain}/"
        if query:
            target = f"{target}?{query}"
        return redirect(target)
    base_path = "/" if is_list_domain else "/minihome/"
    return render(
        request,
        "minihome/list.html",
        {
            "minihomes": minihomes,
            "minihome_base_path": base_path,
        },
    )


def _find_section(sections, section_id, section_type):
    for section in sections:
        if section.get("id") == section_id and section.get("type") == section_type:
            return section
    return None


def _find_item(items, item_id):
    for item in items:
        if item.get("id") == item_id:
            return item
    return None


def _save_sections(minihome, sections):
    normalized = _normalize_sections(sections)
    minihome.draft_sections = normalized
    minihome.published_sections = normalized
    minihome.save(update_fields=["draft_sections", "published_sections", "updated_at"])
    return normalized


@login_required
def minihome_add_gallery_item(request, slug):
    minihome = get_object_or_404(Minihome, slug=slug)
    if not _user_can_manage(minihome, request.user):
        return HttpResponseForbidden("권한이 없습니다.")

    if request.method != "POST":
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    section_id = request.POST.get("section_id")
    if not section_id:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    sections = _normalize_sections(minihome.published_sections)
    section = _find_section(sections, section_id, "gallery")
    if not section:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    description = _limit_text(request.POST.get("description"), 10000)
    image_file = request.FILES.get("image")
    image_meta = None
    if image_file:
        upload_result = upload_minihome_image(
            image_file,
            prefix=f"minihome/{minihome.slug}/gallery",
            target_width=GALLERY_IMAGE_WIDTH,
        )
        if upload_result.get("success"):
            image_meta = {
                "path": upload_result["file_path"],
                "url": upload_result["file_url"],
                "width": upload_result["width"],
                "height": upload_result["height"],
            }

    items = section["data"].get("items", [])
    if not isinstance(items, list):
        items = []
    items.append(
        {
            "id": uuid.uuid4().hex,
            "description": description,
            "image": image_meta,
        }
    )
    section["data"]["items"] = items

    _save_sections(minihome, sections)

    return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))


@login_required
def minihome_add_blog_post(request, slug):
    minihome = get_object_or_404(Minihome, slug=slug)
    if not _user_can_manage(minihome, request.user):
        return HttpResponseForbidden("권한이 없습니다.")

    if request.method != "POST":
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    section_id = request.POST.get("section_id")
    if not section_id:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    sections = _normalize_sections(minihome.published_sections)
    section = _find_section(sections, section_id, "mini_blog")
    if not section:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    body = _limit_text(request.POST.get("body") or request.POST.get("text"), 1000)
    title = _limit_text(request.POST.get("title") or body, 100)
    images = []
    for index in range(4):
        file_field = f"image_{index}"
        image_file = request.FILES.get(file_field)
        image_meta = None
        if image_file:
            upload_result = upload_minihome_image(
                image_file,
                prefix=f"minihome/{minihome.slug}/blog",
                target_width=BLOG_IMAGE_WIDTH,
            )
            if upload_result.get("success"):
                image_meta = {
                    "path": upload_result["file_path"],
                    "url": upload_result["file_url"],
                    "width": upload_result["width"],
                    "height": upload_result["height"],
                }
        images.append(image_meta)

    posts = section["data"].get("posts", [])
    if not isinstance(posts, list):
        posts = []
    posts.append(
        {
            "id": uuid.uuid4().hex,
            "title": title,
            "body": body,
            "images": images,
        }
    )
    section["data"]["posts"] = posts

    _save_sections(minihome, sections)

    return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))


@login_required
def minihome_add_store_item(request, slug):
    minihome = get_object_or_404(Minihome, slug=slug)
    if not _user_can_manage(minihome, request.user):
        return HttpResponseForbidden("권한이 없습니다.")

    if request.method != "POST":
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    section_id = request.POST.get("section_id")
    if not section_id:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    sections = _normalize_sections(minihome.published_sections)
    section = _find_section(sections, section_id, "store")
    if not section:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    name = _limit_text(request.POST.get("name"), 50)
    description = _limit_text(request.POST.get("description"), 100)
    map_url = _limit_text(request.POST.get("map_url"), 200)
    cover_image = None
    image_file = request.FILES.get("cover_image")
    if image_file:
        upload_result = upload_minihome_image(
            image_file,
            prefix=f"minihome/{minihome.slug}/store",
            target_width=STORE_IMAGE_WIDTH,
        )
        if upload_result.get("success"):
            cover_image = {
                "path": upload_result["file_path"],
                "url": upload_result["file_url"],
                "width": upload_result["width"],
                "height": upload_result["height"],
            }

    stores = section["data"].get("stores", [])
    if not isinstance(stores, list):
        stores = []
    stores.append(
        {
            "id": uuid.uuid4().hex,
            "name": name,
            "description": description,
            "map_url": map_url,
            "cover_image": cover_image,
        }
    )
    section["data"]["stores"] = stores

    _save_sections(minihome, sections)

    return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))


@login_required
def minihome_update_gallery_item(request, slug):
    minihome = get_object_or_404(Minihome, slug=slug)
    if not _user_can_manage(minihome, request.user):
        return HttpResponseForbidden("권한이 없습니다.")

    if request.method != "POST":
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    section_id = request.POST.get("section_id")
    item_id = request.POST.get("item_id")
    if not section_id or not item_id:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    sections = _normalize_sections(minihome.published_sections)
    section = _find_section(sections, section_id, "gallery")
    if not section:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    items = section["data"].get("items", [])
    if not isinstance(items, list):
        items = []
    item = _find_item(items, item_id)
    if not item:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    item["description"] = _limit_text(request.POST.get("description"), 10000)
    image_file = request.FILES.get("image")
    if image_file:
        upload_result = upload_minihome_image(
            image_file,
            prefix=f"minihome/{minihome.slug}/gallery",
            target_width=GALLERY_IMAGE_WIDTH,
        )
        if upload_result.get("success"):
            item["image"] = {
                "path": upload_result["file_path"],
                "url": upload_result["file_url"],
                "width": upload_result["width"],
                "height": upload_result["height"],
            }

    section["data"]["items"] = items
    _save_sections(minihome, sections)

    return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))


@login_required
def minihome_delete_gallery_item(request, slug):
    minihome = get_object_or_404(Minihome, slug=slug)
    if not _user_can_manage(minihome, request.user):
        return HttpResponseForbidden("권한이 없습니다.")

    if request.method != "POST":
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    section_id = request.POST.get("section_id")
    item_id = request.POST.get("item_id")
    if not section_id or not item_id:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    sections = _normalize_sections(minihome.published_sections)
    section = _find_section(sections, section_id, "gallery")
    if not section:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    items = section["data"].get("items", [])
    if not isinstance(items, list):
        items = []
    section["data"]["items"] = [item for item in items if item.get("id") != item_id]
    _save_sections(minihome, sections)

    return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))


@login_required
def minihome_update_blog_post(request, slug):
    minihome = get_object_or_404(Minihome, slug=slug)
    if not _user_can_manage(minihome, request.user):
        return HttpResponseForbidden("권한이 없습니다.")

    if request.method != "POST":
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    section_id = request.POST.get("section_id")
    post_id = request.POST.get("post_id")
    if not section_id or not post_id:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    sections = _normalize_sections(minihome.published_sections)
    section = _find_section(sections, section_id, "mini_blog")
    if not section:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    posts = section["data"].get("posts", [])
    if not isinstance(posts, list):
        posts = []
    post = _find_item(posts, post_id)
    if not post:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    body = _limit_text(request.POST.get("body") or request.POST.get("text"), 1000)
    title = _limit_text(request.POST.get("title") or body, 100)
    post["title"] = title
    post["body"] = body
    images = post.get("images", [])
    if not isinstance(images, list):
        images = []
    while len(images) < 4:
        images.append(None)

    for index in range(4):
        image_file = request.FILES.get(f"image_{index}")
        if not image_file:
            continue
        upload_result = upload_minihome_image(
            image_file,
            prefix=f"minihome/{minihome.slug}/blog",
            target_width=BLOG_IMAGE_WIDTH,
        )
        if upload_result.get("success"):
            images[index] = {
                "path": upload_result["file_path"],
                "url": upload_result["file_url"],
                "width": upload_result["width"],
                "height": upload_result["height"],
            }

    post["images"] = images
    section["data"]["posts"] = posts
    _save_sections(minihome, sections)

    return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))


@login_required
def minihome_delete_blog_post(request, slug):
    minihome = get_object_or_404(Minihome, slug=slug)
    if not _user_can_manage(minihome, request.user):
        return HttpResponseForbidden("권한이 없습니다.")

    if request.method != "POST":
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    section_id = request.POST.get("section_id")
    post_id = request.POST.get("post_id")
    if not section_id or not post_id:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    sections = _normalize_sections(minihome.published_sections)
    section = _find_section(sections, section_id, "mini_blog")
    if not section:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    posts = section["data"].get("posts", [])
    if not isinstance(posts, list):
        posts = []
    section["data"]["posts"] = [post for post in posts if post.get("id") != post_id]
    _save_sections(minihome, sections)

    return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))


@login_required
def minihome_update_store_item(request, slug):
    minihome = get_object_or_404(Minihome, slug=slug)
    if not _user_can_manage(minihome, request.user):
        return HttpResponseForbidden("권한이 없습니다.")

    if request.method != "POST":
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    section_id = request.POST.get("section_id")
    store_id = request.POST.get("store_id")
    if not section_id or not store_id:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    sections = _normalize_sections(minihome.published_sections)
    section = _find_section(sections, section_id, "store")
    if not section:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    stores = section["data"].get("stores", [])
    if not isinstance(stores, list):
        stores = []
    store = _find_item(stores, store_id)
    if not store:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    store["name"] = _limit_text(request.POST.get("name"), 50)
    store["description"] = _limit_text(request.POST.get("description"), 100)
    store["map_url"] = _limit_text(request.POST.get("map_url"), 200)
    image_file = request.FILES.get("cover_image")
    if image_file:
        upload_result = upload_minihome_image(
            image_file,
            prefix=f"minihome/{minihome.slug}/store",
            target_width=STORE_IMAGE_WIDTH,
        )
        if upload_result.get("success"):
            store["cover_image"] = {
                "path": upload_result["file_path"],
                "url": upload_result["file_url"],
                "width": upload_result["width"],
                "height": upload_result["height"],
            }

    section["data"]["stores"] = stores
    _save_sections(minihome, sections)

    return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))


@login_required
def minihome_delete_store_item(request, slug):
    minihome = get_object_or_404(Minihome, slug=slug)
    if not _user_can_manage(minihome, request.user):
        return HttpResponseForbidden("권한이 없습니다.")

    if request.method != "POST":
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    section_id = request.POST.get("section_id")
    store_id = request.POST.get("store_id")
    if not section_id or not store_id:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    sections = _normalize_sections(minihome.published_sections)
    section = _find_section(sections, section_id, "store")
    if not section:
        return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))

    stores = section["data"].get("stores", [])
    if not isinstance(stores, list):
        stores = []
    section["data"]["stores"] = [store for store in stores if store.get("id") != store_id]
    _save_sections(minihome, sections)

    return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))


def minihome_landing(request, slug):
    host = request.get_host().split(":")[0]
    list_domain = normalize_domain(settings.MINIHOME_LIST_DOMAIN)
    if list_domain and normalize_domain(host) != list_domain and request.path.startswith("/minihome/"):
        query = request.GET.urlencode()
        target = f"{request.scheme}://{list_domain}/{slug}/"
        if query:
            target = f"{target}?{query}"
        return redirect(target)

    minihome = get_object_or_404(Minihome, slug=slug, is_published=True)
    background_preset = _normalize_background_preset(
        minihome.published_background_preset
    )
    context = {
        "minihome": minihome,
        "sections": _normalize_sections(minihome.published_sections),
        "is_preview": False,
        "background_preset": background_preset,
    }

    if request.user.is_authenticated and _user_can_manage(minihome, request.user):
        path = request.path.strip("/")
        if request.path.startswith("/minihome/"):
            manage_url = reverse("minihome:manage", kwargs={"slug": minihome.slug})
        elif path.startswith(f"{minihome.slug}/") or path == minihome.slug:
            manage_url = f"/{minihome.slug}/mng/"
        else:
            manage_url = "/mng/"
        context["show_manage_link"] = True
        context["manage_url"] = manage_url

    return render(request, "minihome/landing.html", context)


@login_required
def minihome_preview(request, slug):
    minihome = get_object_or_404(Minihome, slug=slug)
    if not _user_can_manage(minihome, request.user):
        return HttpResponseForbidden("권한이 없습니다.")

    sections = _normalize_sections(minihome.draft_sections)
    background_preset = _normalize_background_preset(minihome.draft_background_preset)
    return render(
        request,
        "minihome/landing.html",
        {
            "minihome": minihome,
            "sections": sections,
            "is_preview": True,
            "background_preset": background_preset,
        },
    )


@login_required
def minihome_manage(request, slug):
    minihome = get_object_or_404(Minihome, slug=slug)
    if not _user_can_manage(minihome, request.user):
        return HttpResponseForbidden("권한이 없습니다.")

    if request.method == "POST":
        action = request.POST.get("action", "save")
        payload = request.POST.get("sections_payload", "[]")
        background_preset = _normalize_background_preset(
            request.POST.get("background_preset", minihome.draft_background_preset)
        )
        try:
            sections = json.loads(payload)
        except json.JSONDecodeError:
            sections = []
        sections = _normalize_sections(sections)
        sections = _apply_uploaded_files(minihome, sections, request.FILES)

        minihome.draft_sections = sections
        minihome.draft_background_preset = background_preset
        minihome.save(update_fields=["draft_sections", "draft_background_preset", "updated_at"])

        if action == "publish":
            minihome.published_sections = sections
            minihome.published_background_preset = background_preset
            minihome.is_published = True
            minihome.published_at = timezone.now()
            minihome.save(
                update_fields=[
                    "published_sections",
                    "published_background_preset",
                    "is_published",
                    "published_at",
                    "updated_at",
                ]
            )
            return redirect(f"{reverse('minihome:manage', kwargs={'slug': minihome.slug})}?published=1")
        if action == "preview":
            return redirect(reverse("minihome:preview", kwargs={"slug": minihome.slug}))

    selected_background = _normalize_background_preset(
        minihome.draft_background_preset or minihome.published_background_preset
    )
    selected_background_label = BACKGROUND_PRESET_LABELS.get(
        selected_background,
        BACKGROUND_PRESET_LABELS.get(DEFAULT_BACKGROUND_PRESET, ""),
    )
    sections = _normalize_sections(minihome.draft_sections)
    return render(
        request,
        "minihome/manage.html",
        {
            "minihome": minihome,
            "sections": sections,
            "section_types": SECTION_TYPES,
            "background_presets": BACKGROUND_PRESETS,
            "selected_background": selected_background,
            "selected_background_label": selected_background_label,
        },
    )
