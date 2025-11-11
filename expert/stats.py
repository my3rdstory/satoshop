from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Dict, Iterable

from django.db.models import Count
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from accounts.models import LightningUser
from .models import DirectContractDocument


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


def aggregate_payment_stats(*, window_days: int = 30) -> Dict:
    documents = DirectContractDocument.objects.exclude(payment_meta__isnull=True)
    records = list(_iter_payment_records(documents))
    now = timezone.now()
    window_start = now - timedelta(days=window_days)

    total_amount = sum(record["amount"] for record in records)
    total_count = len(records)

    recent_amount = sum(record["amount"] for record in records if record["paid_at"] and record["paid_at"] >= window_start)
    recent_count = sum(1 for record in records if record["paid_at"] and record["paid_at"] >= window_start)

    role_breakdown: Dict[str, int] = defaultdict(int)
    for record in records:
        role_breakdown[record["role"]] += record["amount"]

    return {
        "total_amount_sats": total_amount,
        "total_count": total_count,
        "recent_amount_sats": recent_amount,
        "recent_count": recent_count,
        "role_breakdown": dict(role_breakdown),
        "window_days": window_days,
    }


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
