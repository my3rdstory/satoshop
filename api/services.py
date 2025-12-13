from django.db.models import Prefetch

from stores.models import Store
from products.models import Product
from meetup.models import Meetup
from lecture.models import LiveLecture
from file.models import DigitalFile
from boards.models import Notice


def get_active_stores_with_relations():
    """활성 스토어와 활성 연관 리소스를 한 번에 로드."""
    product_qs = Product.objects.filter(is_active=True).order_by("-created_at")
    meetup_qs = Meetup.objects.filter(
        is_active=True,
        is_temporarily_closed=False,
        deleted_at__isnull=True,
    ).order_by("-created_at")
    live_qs = LiveLecture.objects.filter(
        is_active=True,
        is_temporarily_closed=False,
        deleted_at__isnull=True,
    ).order_by("-created_at")
    file_qs = DigitalFile.objects.filter(
        is_active=True,
        is_temporarily_closed=False,
        deleted_at__isnull=True,
    ).order_by("-created_at")

    return (
        Store.objects.filter(is_active=True, deleted_at__isnull=True)
        .select_related("owner")
        .prefetch_related(
            Prefetch("products", queryset=product_qs, to_attr="active_products"),
            Prefetch("meetups", queryset=meetup_qs, to_attr="active_meetups"),
            Prefetch("live_lectures", queryset=live_qs, to_attr="active_live_lectures"),
            Prefetch("digital_files", queryset=file_qs, to_attr="active_digital_files"),
        )
        .order_by("store_name")
    )


def get_store_owner(store_id: str):
    """스토어 단건과 주인장 정보 조회."""
    return (
        Store.objects.filter(store_id=store_id, is_active=True, deleted_at__isnull=True)
        .select_related("owner")
        .first()
    )


def get_active_products(store):
    return store.products.filter(is_active=True).order_by("-created_at")


def get_active_meetups(store):
    return store.meetups.filter(is_active=True, is_temporarily_closed=False, deleted_at__isnull=True).order_by("-created_at")


def get_active_live_lectures(store):
    return store.live_lectures.filter(is_active=True, is_temporarily_closed=False, deleted_at__isnull=True).order_by("-created_at")


def get_active_digital_files(store):
    return store.digital_files.filter(is_active=True, is_temporarily_closed=False, deleted_at__isnull=True).order_by("-created_at")


def get_active_notices():
    """활성화된 공지사항 목록을 고정 여부/생성일 역순으로 조회."""
    return (
        Notice.objects.filter(is_active=True)
        .select_related("author")
        .order_by("-is_pinned", "-created_at")
    )
