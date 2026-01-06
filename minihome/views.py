import json
import uuid
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import Minihome
from .services import upload_minihome_image


SECTION_TYPES = (
    "brand_image",
    "title",
    "gallery",
    "mini_blog",
    "store",
    "cta",
)

BRAND_IMAGE_WIDTH = 900
GALLERY_IMAGE_WIDTH = 900
BLOG_IMAGE_WIDTH = 1000
CTA_PROFILE_MAX_SIZE = (300, 300)
STORE_IMAGE_WIDTH = 600


def _user_can_manage(minihome: Minihome, user) -> bool:
    if not user.is_authenticated:
        return False
    return minihome.owners.filter(pk=user.pk).exists()


def _limit_text(value, limit: int) -> str:
    return (value or "").strip()[:limit]


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

        if section_type == "title":
            normalized.append({
                "id": section_id,
                "type": section_type,
                "data": {
                    "title": _limit_text(data.get("title"), 30),
                    "description": _limit_text(data.get("description"), 100),
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
                    "description": _limit_text(item.get("description"), 100),
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
                    "text": _limit_text(post.get("text"), 1000),
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
                    "description": _limit_text(data.get("description"), 200),
                    "email": _limit_text(data.get("email"), 20),
                    "donation": _limit_text(data.get("donation"), 20),
                },
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

    return sections


def minihome_list(request):
    minihomes = Minihome.objects.filter(is_published=True).order_by("-updated_at")
    return render(
        request,
        "minihome/list.html",
        {"minihomes": minihomes},
    )


def _find_section(sections, section_id, section_type):
    for section in sections:
        if section.get("id") == section_id and section.get("type") == section_type:
            return section
    return None


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

    description = _limit_text(request.POST.get("description"), 100)
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

    sections = _normalize_sections(sections)
    minihome.draft_sections = sections
    minihome.published_sections = sections
    minihome.save(update_fields=["draft_sections", "published_sections", "updated_at"])

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

    text = _limit_text(request.POST.get("text"), 1000)
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
            "text": text,
            "images": images,
        }
    )
    section["data"]["posts"] = posts

    sections = _normalize_sections(sections)
    minihome.draft_sections = sections
    minihome.published_sections = sections
    minihome.save(update_fields=["draft_sections", "published_sections", "updated_at"])

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
            "map_url": map_url,
            "cover_image": cover_image,
        }
    )
    section["data"]["stores"] = stores

    sections = _normalize_sections(sections)
    minihome.draft_sections = sections
    minihome.published_sections = sections
    minihome.save(update_fields=["draft_sections", "published_sections", "updated_at"])

    return redirect(reverse("minihome:landing", kwargs={"slug": minihome.slug}))


def minihome_landing(request, slug):
    minihome = get_object_or_404(Minihome, slug=slug)
    if not minihome.is_published:
        raise Http404

    sections = minihome.published_sections
    can_manage = _user_can_manage(minihome, request.user)
    return render(
        request,
        "minihome/landing.html",
        {
            "minihome": minihome,
            "sections": sections,
            "is_preview": False,
            "can_manage": can_manage,
        },
    )


@login_required
def minihome_preview(request, slug):
    minihome = get_object_or_404(Minihome, slug=slug)
    if not _user_can_manage(minihome, request.user):
        return HttpResponseForbidden("권한이 없습니다.")

    sections = minihome.draft_sections
    return render(
        request,
        "minihome/landing.html",
        {
            "minihome": minihome,
            "sections": sections,
            "is_preview": True,
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
        try:
            sections = json.loads(payload)
        except json.JSONDecodeError:
            sections = []
        sections = _normalize_sections(sections)
        sections = _apply_uploaded_files(minihome, sections, request.FILES)

        minihome.draft_sections = sections
        minihome.save(update_fields=["draft_sections", "updated_at"])

        if action == "publish":
            minihome.published_sections = sections
            minihome.is_published = True
            minihome.published_at = timezone.now()
            minihome.save(
                update_fields=[
                    "published_sections",
                    "is_published",
                    "published_at",
                    "updated_at",
                ]
            )
        if action == "preview":
            return redirect(reverse("minihome:preview", kwargs={"slug": minihome.slug}))

    return render(
        request,
        "minihome/manage.html",
        {
            "minihome": minihome,
            "sections": minihome.draft_sections,
            "section_types": SECTION_TYPES,
        },
    )
