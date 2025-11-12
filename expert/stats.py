from __future__ import annotations

from collections import defaultdict
from datetime import timedelta, datetime
from typing import Dict, Iterable, List, Optional

from django.db.models import Count
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from accounts.models import LightningUser
from .models import DirectContractDocument, ContractPricingSetting


def _iter_payment_records(documents: Iterable[DirectContractDocument]) -> Iterable[Dict]:
    for document in documents:
        payment_meta = document.payment_meta or {}
        for role, receipt in payment_meta.items():
            amount = int(receipt.get("amount_sats") or 0)
            if amount <= 0:
                continue
            paid_at = _safe_parse_datetime(receipt.get("paid_at")) or document.updated_at
            yield {
                "amount": amount,
                "role": role,
                "paid_at": paid_at,
                "document": document,
            }


def _safe_parse_datetime(raw_value):
    if not raw_value:
        return None
    dt = parse_datetime(raw_value)
    if not dt:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.utc)
    return dt


def _summarize_records(records: List[Dict], *, window_start=None) -> Dict:
    role_breakdown: Dict[str, int] = defaultdict(int)
    total_amount = 0
    total_count = 0
    recent_amount = 0
    recent_count = 0

    for record in records:
        amount = record["amount"]
        total_amount += amount
        total_count += 1
        role_breakdown[record["role"]] += amount
        paid_at = record.get("paid_at")
        if window_start and paid_at and paid_at >= window_start:
            recent_amount += amount
            recent_count += 1

    return {
        "total_amount_sats": total_amount,
        "total_count": total_count,
        "recent_amount_sats": recent_amount,
        "recent_count": recent_count,
        "role_breakdown": dict(role_breakdown),
    }


def _build_month_options(records: List[Dict]) -> List[Dict]:
    month_map: Dict[str, str] = {}
    tz = timezone.get_current_timezone()
    for record in records:
        paid_at = record.get("paid_at")
        if not paid_at:
            continue
        local_dt = timezone.localtime(paid_at, tz)
        slug = local_dt.strftime("%Y-%m")
        month_map[slug] = local_dt.strftime("%Y년 %m월")
    options = [
        {"value": slug, "label": label}
        for slug, label in sorted(month_map.items(), key=lambda item: item[0], reverse=True)
    ]
    return options


def _filter_records_by_month(records: List[Dict], month_slug: str) -> List[Dict]:
    try:
        year, month = map(int, month_slug.split("-"))
        if month < 1 or month > 12:
            raise ValueError
    except ValueError:
        return []
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime(year, month, 1), timezone=tz)
    if month == 12:
        end = timezone.make_aware(datetime(year + 1, 1, 1), timezone=tz)
    else:
        end = timezone.make_aware(datetime(year, month + 1, 1), timezone=tz)
    filtered: List[Dict] = []
    for record in records:
        paid_at = record.get("paid_at")
        if not paid_at:
            continue
        local_dt = timezone.localtime(paid_at, tz)
        if start <= local_dt < end:
            filtered.append(record)
    return filtered


def _build_month_nav(options: List[Dict], selected_slug: str) -> Dict:
    if not options:
        return {}
    slugs = [opt["value"] for opt in options]
    if selected_slug not in slugs:
        selected_slug = slugs[0]
    idx = slugs.index(selected_slug)
    prev_slug = slugs[idx + 1] if idx + 1 < len(slugs) else ""
    next_slug = slugs[idx - 1] if idx - 1 >= 0 else ""

    def _label(slug: str) -> str:
        if not slug:
            return ""
        for opt in options:
            if opt["value"] == slug:
                return opt["label"]
        return ""

    current_label = _label(selected_slug)
    now_slug = timezone.localtime(timezone.now()).strftime("%Y-%m")
    if selected_slug == now_slug:
        current_label = f"{current_label} (이번 달)"

    return {
        "current_slug": selected_slug,
        "current_label": current_label,
        "prev_slug": prev_slug,
        "prev_label": _label(prev_slug),
        "next_slug": next_slug,
        "next_label": _label(next_slug),
    }


def _serialize_pricing(pricing: Optional[ContractPricingSetting]) -> Optional[Dict]:
    if not pricing:
        return None
    return {
        "name": pricing.name,
        "client_fee_sats": pricing.client_fee_sats,
        "performer_fee_sats": pricing.performer_fee_sats,
        "updated_at": pricing.updated_at,
        "enabled": pricing.enabled,
    }


def aggregate_payment_stats(*, window_days: int = 30, month_slug: str | None = None) -> Dict:
    documents = DirectContractDocument.objects.exclude(payment_meta__isnull=True)
    records = list(_iter_payment_records(documents))
    now = timezone.now()
    window_start = now - timedelta(days=window_days)

    summary = _summarize_records(records, window_start=window_start)
    summary["window_days"] = window_days

    month_options = _build_month_options(records)
    cleaned_month_slug = month_slug.strip() if month_slug else ""
    month_nav = _build_month_nav(month_options, cleaned_month_slug) if month_options else {}

    filtered_stats = None
    if month_nav:
        nav_slug = month_nav["current_slug"]
        filtered_records = _filter_records_by_month(records, nav_slug)
        filtered_summary = _summarize_records(filtered_records, window_start=None)
        filtered_summary.update(
            {
                "label": month_nav["current_label"],
                "slug": nav_slug,
            }
        )
        filtered_stats = filtered_summary

    pricing = _serialize_pricing(
        ContractPricingSetting.objects.filter(enabled=True).order_by("-pk").first()
    )

    summary.update(
        {
            "month_options": month_options,
            "selected_month": month_nav.get("current_slug", "") if month_nav else "",
            "selected_month_label": month_nav.get("current_label", "") if month_nav else "",
            "filtered_stats": filtered_stats,
            "month_nav": month_nav,
            "pricing": pricing,
        }
    )
    return summary


def aggregate_usage_stats(*, window_days: int = 30) -> Dict:
    contracts = DirectContractDocument.objects.all()
    total_contracts = contracts.count()
    completed_contracts = contracts.filter(status="completed").count()

    total_amount = 0
    for payload in contracts.values_list("payload", flat=True):
        if not isinstance(payload, dict):
            continue
        try:
            total_amount += int(payload.get("amount_sats") or 0)
        except (TypeError, ValueError):
            continue

    unique_creators = contracts.exclude(creator__isnull=True).values("creator_id").distinct().count()
    unique_counterparties = contracts.exclude(counterparty_user__isnull=True).values("counterparty_user_id").distinct().count()

    lightning_users_total = LightningUser.objects.count()
    lightning_active = LightningUser.objects.filter(last_login_at__gte=timezone.now() - timedelta(days=window_days)).count()

    payment_stats = aggregate_payment_stats(window_days=window_days)

    return {
        "contracts_total": total_contracts,
        "contracts_completed": completed_contracts,
        "contract_amount_sats": total_amount,
        "unique_creators": unique_creators,
        "unique_counterparties": unique_counterparties,
        "lightning_users_total": lightning_users_total,
        "lightning_users_active": lightning_active,
        "payments": payment_stats,
    }
