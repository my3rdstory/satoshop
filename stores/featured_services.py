from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Sequence

from django.db import transaction
from django.utils import timezone

from products.models import Product
from meetup.models import Meetup
from lecture.models import LiveLecture
from file.models import DigitalFile

from .constants import (
    FEATURE_ITEM_TYPE_FILE,
    FEATURE_ITEM_TYPE_LIVE,
    FEATURE_ITEM_TYPE_MEETUP,
    FEATURE_ITEM_TYPE_PRODUCT,
    STORE_MAIN_DISPLAY_LIMITS,
)
from .models import Store, StoreFeaturedItem


@dataclass(frozen=True)
class FeaturedSectionConfig:
    key: str
    label: str
    icon: str
    accent_from: str
    accent_to: str
    limit: int
    helper_text: str
    empty_text: str
    type_description: str


FEATURED_SECTION_CONFIGS: Dict[str, FeaturedSectionConfig] = {
    FEATURE_ITEM_TYPE_PRODUCT: FeaturedSectionConfig(
        key=FEATURE_ITEM_TYPE_PRODUCT,
        label='상품',
        icon='fa-shopping-bag',
        accent_from='from-amber-500',
        accent_to='to-orange-500',
        limit=STORE_MAIN_DISPLAY_LIMITS[FEATURE_ITEM_TYPE_PRODUCT],
        helper_text='활성화된 상품 중 최대 8개까지 대문에 노출됩니다.',
        empty_text='활성화된 상품이 없습니다. 상품을 먼저 등록하거나 활성화하세요.',
        type_description='상품을 클릭해 대문에서 보여줄 순서를 지정하고, 필요하면 위/아래 버튼으로 미세 조정하세요.',
    ),
    FEATURE_ITEM_TYPE_MEETUP: FeaturedSectionConfig(
        key=FEATURE_ITEM_TYPE_MEETUP,
        label='밋업',
        icon='fa-users',
        accent_from='from-purple-500',
        accent_to='to-fuchsia-500',
        limit=STORE_MAIN_DISPLAY_LIMITS[FEATURE_ITEM_TYPE_MEETUP],
        helper_text='최대 8개의 밋업이 메인에 노출됩니다.',
        empty_text='활성화된 밋업이 없습니다. 밋업을 등록한 뒤 활성화하세요.',
        type_description='예정된 밋업 중에서 우선 노출할 일정을 선택하세요. 클릭 순서대로 정렬됩니다.',
    ),
    FEATURE_ITEM_TYPE_LIVE: FeaturedSectionConfig(
        key=FEATURE_ITEM_TYPE_LIVE,
        label='라이브 강의',
        icon='fa-video',
        accent_from='from-emerald-500',
        accent_to='to-lime-500',
        limit=STORE_MAIN_DISPLAY_LIMITS[FEATURE_ITEM_TYPE_LIVE],
        helper_text='라이브 강의 역시 최대 8개까지만 대문 상단에 노출됩니다.',
        empty_text='활성화된 라이브 강의가 없습니다. 강의를 등록해 주세요.',
        type_description='강의를 클릭하면 선택 영역에 추가되고, 위/아래 버튼으로 순서를 바꿀 수 있습니다.',
    ),
    FEATURE_ITEM_TYPE_FILE: FeaturedSectionConfig(
        key=FEATURE_ITEM_TYPE_FILE,
        label='디지털 파일',
        icon='fa-file-arrow-down',
        accent_from='from-indigo-500',
        accent_to='to-blue-500',
        limit=STORE_MAIN_DISPLAY_LIMITS[FEATURE_ITEM_TYPE_FILE],
        helper_text='다운로드 상품은 최대 8개까지만 대문에 노출됩니다.',
        empty_text='활성화된 디지털 파일이 없습니다. 파일을 등록하거나 활성화하세요.',
        type_description='판매 중인 디지털 파일을 클릭해 노출 순서를 빠르게 지정하세요.',
    ),
}


def get_section_configs() -> List[FeaturedSectionConfig]:
    return list(FEATURED_SECTION_CONFIGS.values())


def _get_config(item_type: str) -> FeaturedSectionConfig:
    try:
        return FEATURED_SECTION_CONFIGS[item_type]
    except KeyError as exc:  # pragma: no cover - 방어 코드
        raise ValueError('지원하지 않는 노출 항목입니다.') from exc


def _get_queryset(store: Store, item_type: str):
    if item_type == FEATURE_ITEM_TYPE_PRODUCT:
        return store.products.filter(is_active=True).order_by('-created_at')
    if item_type == FEATURE_ITEM_TYPE_MEETUP:
        return store.meetups.filter(is_active=True, deleted_at__isnull=True).order_by('-created_at')
    if item_type == FEATURE_ITEM_TYPE_LIVE:
        return store.live_lectures.filter(is_active=True, deleted_at__isnull=True).order_by('-created_at')
    if item_type == FEATURE_ITEM_TYPE_FILE:
        return store.digital_files.filter(is_active=True, deleted_at__isnull=True).order_by('-created_at')
    raise ValueError('지원하지 않는 노출 항목입니다.')


def _format_price(value: int | None, unit: str) -> str:
    if value is None:
        return '가격 미정'
    if unit == 'sats':
        return f"{int(value):,} sats"
    return f"{int(value):,}{unit}"


def _format_datetime(dt) -> str:
    if not dt:
        return '일정 미정'
    localized = timezone.localtime(dt)
    return localized.strftime('%Y-%m-%d %H:%M')


def _serialize_item(item_type: str, obj) -> Dict:
    if item_type == FEATURE_ITEM_TYPE_PRODUCT:
        unit = '원' if getattr(obj, 'price_display', '') == 'krw' else 'sats'
        meta_secondary = f"재고 {obj.stock_quantity:,}개" if obj.stock_quantity else '재고 수량 없음'
        payload = {
            'id': obj.id,
            'title': obj.title,
            'meta_primary': _format_price(obj.display_price, unit),
            'meta_secondary': meta_secondary,
            'badge': '할인' if obj.is_discounted and obj.display_discounted_price else '',
        }
        return payload

    if item_type == FEATURE_ITEM_TYPE_MEETUP:
        meta_primary = _format_datetime(obj.date_time)
        price_text = '무료 이벤트' if obj.is_free else _format_price(obj.price, 'sats')
        payload = {
            'id': obj.id,
            'title': obj.name,
            'meta_primary': meta_primary,
            'meta_secondary': price_text,
            'badge': '할인' if obj.is_discounted else '',
        }
        return payload

    if item_type == FEATURE_ITEM_TYPE_LIVE:
        unit = '원' if obj.price_display == 'krw' else 'sats'
        price_value = 0 if obj.price_display == 'free' else obj.current_price
        price_text = '무료 강의' if obj.price_display == 'free' else _format_price(price_value, unit)
        payload = {
            'id': obj.id,
            'title': obj.name,
            'meta_primary': _format_datetime(obj.date_time),
            'meta_secondary': price_text,
            'badge': '할인' if obj.is_discounted else '',
        }
        return payload

    if item_type == FEATURE_ITEM_TYPE_FILE:
        unit = '원' if obj.price_display == 'krw' else 'sats'
        if obj.price_display == 'free':
            price_text = '무료'
        else:
            price_text = _format_price(obj.current_price, unit)
        file_type = ''
        if hasattr(obj, 'get_file_type_display'):
            file_type = obj.get_file_type_display()
        payload = {
            'id': obj.id,
            'title': obj.name,
            'meta_primary': price_text,
            'meta_secondary': file_type or obj.get_file_size_display(),
            'badge': '할인' if obj.is_discounted and obj.is_discount_active else '',
        }
        return payload

    raise ValueError('지원하지 않는 노출 항목입니다.')


def _get_selected_ids(store: Store, item_type: str) -> List[int]:
    config = _get_config(item_type)
    selected_qs = (
        StoreFeaturedItem.objects
        .filter(store=store, item_type=item_type)
        .order_by('order', 'created_at')
    )
    return list(selected_qs.values_list('object_id', flat=True))[: config.limit]


def get_featured_sections_for_editor(store: Store) -> List[Dict]:
    sections: List[Dict] = []
    for config in get_section_configs():
        items = list(_get_queryset(store, config.key))
        serialized_items = []
        for obj in items:
            payload = _serialize_item(config.key, obj)
            serialized_items.append(payload)
        payload_map = {item['id']: item for item in serialized_items}
        selected_ids = _get_selected_ids(store, config.key)
        stale_ids = [item_id for item_id in selected_ids if item_id not in payload_map]
        if stale_ids:
            StoreFeaturedItem.objects.filter(
                store=store,
                item_type=config.key,
                object_id__in=stale_ids,
            ).delete()
            selected_ids = [item_id for item_id in selected_ids if item_id in payload_map]
        selected_items = [payload_map[item_id] for item_id in selected_ids]
        sections.append({
            'config': config,
            'available_items': serialized_items,
            'selected_items': selected_items,
            'selected_ids': selected_ids,
            'active_count': len(serialized_items),
        })
    return sections


def get_featured_items_for_display(store: Store, item_type: str) -> List:
    config = _get_config(item_type)
    queryset = _get_queryset(store, item_type)
    selected_ids = _get_selected_ids(store, item_type)
    if not selected_ids:
        return list(queryset[:config.limit])

    selected_objects = queryset.filter(id__in=selected_ids)
    selected_map = {obj.id: obj for obj in selected_objects}
    ordered_selected = [selected_map[item_id] for item_id in selected_ids if item_id in selected_map]

    if len(ordered_selected) >= config.limit:
        return ordered_selected[:config.limit]

    remaining_needed = config.limit - len(ordered_selected)
    fallback_items = list(queryset.exclude(id__in=selected_map.keys())[:remaining_needed])
    return ordered_selected + fallback_items


def save_featured_order(store: Store, item_type: str, object_ids: Sequence[int | str]) -> List[int]:
    config = _get_config(item_type)
    normalized_ids: List[int] = []
    seen = set()
    for object_id in object_ids:
        try:
            parsed = int(object_id)
        except (TypeError, ValueError):
            continue
        if parsed in seen:
            continue
        seen.add(parsed)
        normalized_ids.append(parsed)
    if len(normalized_ids) > config.limit:
        raise ValueError(f"{config.label}은(는) 최대 {config.limit}개까지만 선택할 수 있습니다.")

    valid_ids = set(_get_queryset(store, item_type).values_list('id', flat=True))
    invalid_ids = [object_id for object_id in normalized_ids if object_id not in valid_ids]
    if invalid_ids:
        raise ValueError('활성 상태가 아닌 항목이 포함되어 있습니다. 새로고침 후 다시 시도하세요.')

    with transaction.atomic():
        StoreFeaturedItem.objects.filter(store=store, item_type=item_type).exclude(
            object_id__in=normalized_ids,
        ).delete()
        for order, object_id in enumerate(normalized_ids, start=1):
            StoreFeaturedItem.objects.update_or_create(
                store=store,
                item_type=item_type,
                object_id=object_id,
                defaults={'order': order},
            )
    return normalized_ids
