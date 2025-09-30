"""결제/체크아웃 관련 공통 유틸."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from stores.models import Store


@dataclass
class StoreItemGroup:
    store: Store
    items: List[Dict]
    subtotal: int
    shipping_fee: int
    total: int
    shipping_info: Dict
    force_free_override: bool


def calculate_store_totals(store_obj: Store, store_items: Iterable[Dict]) -> Tuple[int, int, bool]:
    subtotal = 0
    apply_override = store_obj.shipping_fee_mode == "flat"
    has_items = False

    for item in store_items:
        has_items = True
        subtotal += item.get("total_price", 0) or 0
        item_force_free = item.get("force_free_shipping", False)
        apply_override = apply_override and item_force_free

    if not has_items:
        apply_override = False

    shipping_fee = 0 if apply_override else store_obj.get_shipping_fee_sats(subtotal)
    return subtotal, shipping_fee, apply_override


def group_cart_items(cart_items: Iterable[Dict]) -> List[StoreItemGroup]:
    grouped: Dict[str, Dict] = {}
    for item in cart_items:
        store_id = item["store_id"]
        grouped.setdefault(store_id, {"items": []})["items"].append(item)

    store_groups: List[StoreItemGroup] = []
    for store_id, data in grouped.items():
        store_obj = Store.objects.filter(store_id=store_id, deleted_at__isnull=True).first()
        if not store_obj:
            continue
        subtotal, shipping_fee, override_free = calculate_store_totals(store_obj, data["items"])
        total = subtotal + shipping_fee
        store_groups.append(
            StoreItemGroup(
                store=store_obj,
                items=data["items"],
                subtotal=subtotal,
                shipping_fee=shipping_fee,
                total=total,
                shipping_info=store_obj.get_shipping_fee_display(),
                force_free_override=override_free,
            )
        )
    return store_groups


def calculate_totals(cart_items: Iterable[Dict]) -> Tuple[List[StoreItemGroup], int, int, int]:
    groups = group_cart_items(cart_items)
    subtotal = sum(group.subtotal for group in groups)
    shipping_fee = sum(group.shipping_fee for group in groups)
    total = subtotal + shipping_fee
    return groups, subtotal, shipping_fee, total
