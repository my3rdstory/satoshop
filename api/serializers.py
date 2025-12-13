from typing import List, Optional

from django.utils import timezone

from stores.models import Store
from products.models import Product
from meetup.models import Meetup
from lecture.models import LiveLecture
from file.models import DigitalFile
from boards.models import Notice


def _format_datetime(value) -> Optional[str]:
    if not value:
        return None
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
    return value.isoformat()


def serialize_product(product: Product) -> dict:
    display_currency = "krw" if product.price_display == "krw" else "sats"
    display_price = product.display_price
    display_discounted_price = product.display_discounted_price
    pay_price_sats = product.public_price
    pay_discounted_price_sats = product.public_discounted_price

    return {
        "id": product.id,
        "title": product.title,
        "thumbnail": product.images.first().file_url if hasattr(product, "images") and product.images.exists() else None,
        "pricing_mode": product.price_display,
        "display_currency": display_currency,
        "display_price": display_price,
        "display_discounted_price": display_discounted_price,
        "pay_price_sats": pay_price_sats,
        "pay_discounted_price_sats": pay_discounted_price_sats,
        "is_discounted": product.is_discounted,
        "stock_quantity": product.stock_quantity,
        "is_out_of_stock": product.is_temporarily_out_of_stock,
        "created_at": _format_datetime(product.created_at),
        "updated_at": _format_datetime(product.updated_at),
    }


def serialize_meetup(meetup: Meetup) -> dict:
    display_currency = "sats"
    display_price = 0 if meetup.is_free else meetup.price
    display_discounted_price = meetup.discounted_price if meetup.is_discounted else None
    pay_price_sats = display_price
    pay_discounted_price_sats = display_discounted_price

    return {
        "id": meetup.id,
        "name": meetup.name,
        "date_time": _format_datetime(meetup.date_time),
        "location": meetup.location_full_address,
        "is_free": meetup.is_free,
        "is_discounted": meetup.is_discounted,
        "pricing_mode": "sats",
        "display_currency": display_currency,
        "display_price": display_price,
        "display_discounted_price": display_discounted_price,
        "pay_price_sats": pay_price_sats,
        "pay_discounted_price_sats": pay_discounted_price_sats,
        "status": meetup.status_display,
        "created_at": _format_datetime(meetup.created_at),
        "updated_at": _format_datetime(meetup.updated_at),
    }


def serialize_live_lecture(live_lecture: LiveLecture) -> dict:
    pricing_mode = live_lecture.price_display
    display_currency = "krw" if pricing_mode == "krw" else "sats"
    display_price = live_lecture.display_price
    display_discounted_price = live_lecture.display_discounted_price

    if pricing_mode == "free":
        pay_price_sats = 0
        pay_discounted_price_sats = 0 if live_lecture.is_discounted else None
    elif pricing_mode == "krw":
        pay_price_sats = live_lecture.public_price_krw
        pay_discounted_price_sats = live_lecture.public_discounted_price_krw if live_lecture.is_discounted else None
    else:
        pay_price_sats = live_lecture.price
        pay_discounted_price_sats = live_lecture.discounted_price if live_lecture.is_discounted else None

    return {
        "id": live_lecture.id,
        "name": live_lecture.name,
        "thumbnail": live_lecture.images.first().file_url if hasattr(live_lecture, "images") and live_lecture.images.exists() else None,
        "date_time": _format_datetime(live_lecture.date_time),
        "pricing_mode": pricing_mode,
        "display_currency": display_currency,
        "display_price": display_price,
        "display_discounted_price": display_discounted_price,
        "pay_price_sats": pay_price_sats,
        "pay_discounted_price_sats": pay_discounted_price_sats,
        "is_discounted": live_lecture.is_discounted,
        "is_free": live_lecture.price_display == "free",
        "created_at": _format_datetime(live_lecture.created_at),
        "updated_at": _format_datetime(live_lecture.updated_at),
    }


def serialize_digital_file(digital_file: DigitalFile) -> dict:
    pricing_mode = digital_file.price_display
    display_currency = "krw" if pricing_mode == "krw" else "sats"
    if pricing_mode == "free":
        display_price = 0
        display_discounted_price = None
        pay_price_sats = 0
        pay_discounted_price_sats = None
    else:
        display_price = digital_file.price_krw if pricing_mode == "krw" else digital_file.price
        display_discounted_price = None
        if digital_file.is_discounted:
            display_discounted_price = digital_file.discounted_price_krw if pricing_mode == "krw" else digital_file.discounted_price
        pay_price_sats = digital_file.price_sats
        pay_discounted_price_sats = None
        if digital_file.is_discounted:
            if pricing_mode == "krw":
                from myshop.models import ExchangeRate

                latest_rate = ExchangeRate.get_latest_rate()
                if latest_rate and latest_rate.btc_krw_rate and latest_rate.btc_krw_rate > 0 and digital_file.discounted_price_krw is not None:
                    btc_amount = digital_file.discounted_price_krw / float(latest_rate.btc_krw_rate)
                    pay_discounted_price_sats = round(btc_amount * 100_000_000)
            else:
                pay_discounted_price_sats = digital_file.discounted_price

    return {
        "id": digital_file.id,
        "name": digital_file.name,
        "thumbnail": digital_file.preview_image.url if digital_file.preview_image else None,
        "pricing_mode": pricing_mode,
        "display_currency": display_currency,
        "display_price": display_price,
        "display_discounted_price": display_discounted_price,
        "pay_price_sats": pay_price_sats,
        "pay_discounted_price_sats": pay_discounted_price_sats,
        "is_discounted": digital_file.is_discounted,
        "created_at": _format_datetime(digital_file.created_at),
        "updated_at": _format_datetime(digital_file.updated_at),
    }


def serialize_store(store: Store) -> dict:
    products: List[Product] = getattr(store, "active_products", [])
    meetups: List[Meetup] = getattr(store, "active_meetups", [])
    live_lectures: List[LiveLecture] = getattr(store, "active_live_lectures", [])
    digital_files: List[DigitalFile] = getattr(store, "active_digital_files", [])

    return {
        "id": store.id,
        "store_id": store.store_id,
        "name": store.store_name,
        "description": store.store_description,
        "owner": {
            "name": store.owner_name,
            "phone": store.owner_phone,
            "email": store.owner_email,
            "chat_channel": store.chat_channel,
        },
        "products": [serialize_product(product) for product in products],
        "meetups": [serialize_meetup(meetup) for meetup in meetups],
        "live_lectures": [serialize_live_lecture(live_lecture) for live_lecture in live_lectures],
        "digital_files": [serialize_digital_file(digital_file) for digital_file in digital_files],
        "updated_at": _format_datetime(store.updated_at),
    }


def serialize_store_list(stores) -> dict:
    return {"stores": [serialize_store(store) for store in stores]}


def serialize_store_owner(store: Store) -> dict:
    return {
        "id": store.id,
        "store_id": store.store_id,
        "name": store.store_name,
        "owner": {
            "name": store.owner_name,
            "phone": store.owner_phone,
            "email": store.owner_email,
            "chat_channel": store.chat_channel,
        },
        "updated_at": _format_datetime(store.updated_at),
    }


def serialize_store_item_payload(store: Store, items: list, serializer_fn):
    return {
        "store": {
            "id": store.id,
            "store_id": store.store_id,
            "name": store.store_name,
        },
        "items": [serializer_fn(item) for item in items],
    }


def serialize_notice_summary(notice: Notice) -> dict:
    return {
        "id": notice.id,
        "title": notice.title,
        "content": notice.content,
        "is_pinned": notice.is_pinned,
        "created_at": _format_datetime(notice.created_at),
        "updated_at": _format_datetime(notice.updated_at),
    }


def serialize_notice_detail(notice: Notice) -> dict:
    return {
        "id": notice.id,
        "title": notice.title,
        "content": notice.content,
        "is_pinned": notice.is_pinned,
        "created_at": _format_datetime(notice.created_at),
        "updated_at": _format_datetime(notice.updated_at),
        "author": {
            "id": notice.author.id,
            "username": notice.author.username,
        },
    }
