from __future__ import annotations

from typing import Dict, List

from django.db.models import Count, Max, Sum
from django.db.models.functions import Coalesce

from file.models import DigitalFile, FileOrder
from lecture.models import LiveLecture, LiveLectureOrder
from meetup.models import Meetup, MeetupOrder
from orders.models import OrderItem
from products.models import Product

ITEM_TYPE_PRODUCT = "product"
ITEM_TYPE_MEETUP = "meetup"
ITEM_TYPE_LIVE_LECTURE = "live_lecture"
ITEM_TYPE_DIGITAL_FILE = "digital_file"

PAID_ORDER_STATUSES = ("paid", "shipped", "delivered")

ITEM_TYPE_LABELS = {
    ITEM_TYPE_PRODUCT: "상품",
    ITEM_TYPE_MEETUP: "밋업",
    ITEM_TYPE_LIVE_LECTURE: "라이브강의",
    ITEM_TYPE_DIGITAL_FILE: "디지털파일",
}


def format_sats(value: int | None) -> str:
    sats = int(value or 0)
    return f"{sats:,} sats"


def build_price_text(price_sats: int | None) -> str:
    return format_sats(price_sats)


def build_sold_price_text(price_sats: int | None, sales_count: int) -> str:
    return format_sats(price_sats)


def _product_price_sats(product: Product) -> int:
    if product.is_discounted and product.public_discounted_price:
        return int(product.public_discounted_price)
    return int(product.public_price or 0)


def _meetup_price_sats(meetup: Meetup) -> int:
    return int(meetup.current_price or 0)


def _live_lecture_price_sats(live_lecture: LiveLecture) -> int:
    return int(live_lecture.current_price or 0)


def _digital_file_price_sats(digital_file: DigitalFile) -> int:
    return int(digital_file.current_price_sats or 0)


def get_recent_registered_items(limit: int = 20) -> List[dict]:
    per_type_limit = max(limit, 20)

    products = list(
        Product.objects.filter(
            is_active=True,
            store__is_active=True,
            store__deleted_at__isnull=True,
        )
        .select_related("store")
        .order_by("-created_at")[:per_type_limit]
    )
    meetups = list(
        Meetup.objects.filter(
            is_active=True,
            deleted_at__isnull=True,
            store__is_active=True,
            store__deleted_at__isnull=True,
        )
        .select_related("store")
        .order_by("-created_at")[:per_type_limit]
    )
    live_lectures = list(
        LiveLecture.objects.filter(
            is_active=True,
            deleted_at__isnull=True,
            store__is_active=True,
            store__deleted_at__isnull=True,
        )
        .select_related("store")
        .order_by("-created_at")[:per_type_limit]
    )
    digital_files = list(
        DigitalFile.objects.filter(
            is_active=True,
            deleted_at__isnull=True,
            store__is_active=True,
            store__deleted_at__isnull=True,
        )
        .select_related("store")
        .order_by("-created_at")[:per_type_limit]
    )

    items: List[dict] = []
    for product in products:
        price_sats = _product_price_sats(product)
        items.append(
            {
                "item_type": ITEM_TYPE_PRODUCT,
                "item_type_label": ITEM_TYPE_LABELS[ITEM_TYPE_PRODUCT],
                "item_id": product.id,
                "store_id": product.store.store_id,
                "title": product.title,
                "price_sats": price_sats,
                "price_text": build_price_text(price_sats),
                "event_at": product.created_at,
            }
        )
    for meetup in meetups:
        price_sats = _meetup_price_sats(meetup)
        items.append(
            {
                "item_type": ITEM_TYPE_MEETUP,
                "item_type_label": ITEM_TYPE_LABELS[ITEM_TYPE_MEETUP],
                "item_id": meetup.id,
                "store_id": meetup.store.store_id,
                "title": meetup.name,
                "price_sats": price_sats,
                "price_text": build_price_text(price_sats),
                "event_at": meetup.created_at,
            }
        )
    for live_lecture in live_lectures:
        price_sats = _live_lecture_price_sats(live_lecture)
        items.append(
            {
                "item_type": ITEM_TYPE_LIVE_LECTURE,
                "item_type_label": ITEM_TYPE_LABELS[ITEM_TYPE_LIVE_LECTURE],
                "item_id": live_lecture.id,
                "store_id": live_lecture.store.store_id,
                "title": live_lecture.name,
                "price_sats": price_sats,
                "price_text": build_price_text(price_sats),
                "event_at": live_lecture.created_at,
            }
        )
    for digital_file in digital_files:
        price_sats = _digital_file_price_sats(digital_file)
        items.append(
            {
                "item_type": ITEM_TYPE_DIGITAL_FILE,
                "item_type_label": ITEM_TYPE_LABELS[ITEM_TYPE_DIGITAL_FILE],
                "item_id": digital_file.id,
                "store_id": digital_file.store.store_id,
                "title": digital_file.name,
                "price_sats": price_sats,
                "price_text": build_price_text(price_sats),
                "event_at": digital_file.created_at,
            }
        )

    items.sort(key=lambda item: item["event_at"], reverse=True)
    return items[:limit]


def get_recent_sold_items(limit: int = 20) -> List[dict]:
    per_type_limit = max(limit, 20)
    items: List[dict] = []

    product_sales_rows = list(
        OrderItem.objects.filter(
            order__status__in=PAID_ORDER_STATUSES,
            product__is_active=True,
            product__store__is_active=True,
            product__store__deleted_at__isnull=True,
        )
        .values("product_id")
        .annotate(
            latest_sold_at=Max(Coalesce("order__paid_at", "order__created_at")),
            sales_count=Coalesce(Sum("quantity"), 0),
        )
        .order_by("-latest_sold_at")[:per_type_limit]
    )
    product_ids = [row["product_id"] for row in product_sales_rows if row["product_id"]]
    products = {
        product.id: product
        for product in Product.objects.filter(id__in=product_ids).select_related("store")
    }
    for row in product_sales_rows:
        product = products.get(row["product_id"])
        if not product:
            continue
        sales_count = int(row["sales_count"] or 0)
        price_sats = _product_price_sats(product)
        items.append(
            {
                "item_type": ITEM_TYPE_PRODUCT,
                "item_type_label": ITEM_TYPE_LABELS[ITEM_TYPE_PRODUCT],
                "item_id": product.id,
                "store_id": product.store.store_id,
                "title": product.title,
                "price_sats": price_sats,
                "sales_count": sales_count,
                "price_text": build_sold_price_text(price_sats, sales_count),
                "event_at": row["latest_sold_at"],
            }
        )

    meetup_sales_rows = list(
        MeetupOrder.objects.filter(
            status__in=["confirmed", "completed"],
            meetup__is_active=True,
            meetup__deleted_at__isnull=True,
            meetup__store__is_active=True,
            meetup__store__deleted_at__isnull=True,
        )
        .values("meetup_id")
        .annotate(
            latest_sold_at=Max(Coalesce("paid_at", "created_at")),
            sales_count=Count("id"),
        )
        .order_by("-latest_sold_at")[:per_type_limit]
    )
    meetup_ids = [row["meetup_id"] for row in meetup_sales_rows if row["meetup_id"]]
    meetups = {
        meetup.id: meetup
        for meetup in Meetup.objects.filter(id__in=meetup_ids).select_related("store")
    }
    for row in meetup_sales_rows:
        meetup = meetups.get(row["meetup_id"])
        if not meetup:
            continue
        sales_count = int(row["sales_count"] or 0)
        price_sats = _meetup_price_sats(meetup)
        items.append(
            {
                "item_type": ITEM_TYPE_MEETUP,
                "item_type_label": ITEM_TYPE_LABELS[ITEM_TYPE_MEETUP],
                "item_id": meetup.id,
                "store_id": meetup.store.store_id,
                "title": meetup.name,
                "price_sats": price_sats,
                "sales_count": sales_count,
                "price_text": build_sold_price_text(price_sats, sales_count),
                "event_at": row["latest_sold_at"],
            }
        )

    live_lecture_sales_rows = list(
        LiveLectureOrder.objects.filter(
            status__in=["confirmed", "completed"],
            live_lecture__is_active=True,
            live_lecture__deleted_at__isnull=True,
            live_lecture__store__is_active=True,
            live_lecture__store__deleted_at__isnull=True,
        )
        .values("live_lecture_id")
        .annotate(
            latest_sold_at=Max(Coalesce("paid_at", "created_at")),
            sales_count=Count("id"),
        )
        .order_by("-latest_sold_at")[:per_type_limit]
    )
    live_lecture_ids = [row["live_lecture_id"] for row in live_lecture_sales_rows if row["live_lecture_id"]]
    live_lectures = {
        live_lecture.id: live_lecture
        for live_lecture in LiveLecture.objects.filter(id__in=live_lecture_ids).select_related("store")
    }
    for row in live_lecture_sales_rows:
        live_lecture = live_lectures.get(row["live_lecture_id"])
        if not live_lecture:
            continue
        sales_count = int(row["sales_count"] or 0)
        price_sats = _live_lecture_price_sats(live_lecture)
        items.append(
            {
                "item_type": ITEM_TYPE_LIVE_LECTURE,
                "item_type_label": ITEM_TYPE_LABELS[ITEM_TYPE_LIVE_LECTURE],
                "item_id": live_lecture.id,
                "store_id": live_lecture.store.store_id,
                "title": live_lecture.name,
                "price_sats": price_sats,
                "sales_count": sales_count,
                "price_text": build_sold_price_text(price_sats, sales_count),
                "event_at": row["latest_sold_at"],
            }
        )

    file_sales_rows = list(
        FileOrder.objects.filter(
            status="confirmed",
            digital_file__is_active=True,
            digital_file__deleted_at__isnull=True,
            digital_file__store__is_active=True,
            digital_file__store__deleted_at__isnull=True,
        )
        .values("digital_file_id")
        .annotate(
            latest_sold_at=Max(Coalesce("paid_at", "created_at")),
            sales_count=Count("id"),
        )
        .order_by("-latest_sold_at")[:per_type_limit]
    )
    file_ids = [row["digital_file_id"] for row in file_sales_rows if row["digital_file_id"]]
    digital_files = {
        digital_file.id: digital_file
        for digital_file in DigitalFile.objects.filter(id__in=file_ids).select_related("store")
    }
    for row in file_sales_rows:
        digital_file = digital_files.get(row["digital_file_id"])
        if not digital_file:
            continue
        sales_count = int(row["sales_count"] or 0)
        price_sats = _digital_file_price_sats(digital_file)
        items.append(
            {
                "item_type": ITEM_TYPE_DIGITAL_FILE,
                "item_type_label": ITEM_TYPE_LABELS[ITEM_TYPE_DIGITAL_FILE],
                "item_id": digital_file.id,
                "store_id": digital_file.store.store_id,
                "title": digital_file.name,
                "price_sats": price_sats,
                "sales_count": sales_count,
                "price_text": build_sold_price_text(price_sats, sales_count),
                "event_at": row["latest_sold_at"],
            }
        )

    items = [item for item in items if item.get("event_at")]
    items.sort(key=lambda item: item["event_at"], reverse=True)
    return items[:limit]


def build_recent_items_lookup(items: List[dict]) -> Dict[str, dict]:
    lookup: Dict[str, dict] = {}
    for item in items:
        key = f"{item['item_type']}:{item['item_id']}"
        lookup[key] = item
    return lookup
