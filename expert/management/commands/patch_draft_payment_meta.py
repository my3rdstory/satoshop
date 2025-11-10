from django.core.management.base import BaseCommand

from expert.models import DirectContractDocument, DirectContractStageLog


class Command(BaseCommand):
    help = "Ensure creator payment receipts are persisted on DirectContractDocument.payment_meta"

    def handle(self, *args, **options):
        patched = 0
        logs = (
            DirectContractStageLog.objects.filter(stage="draft", document__isnull=False)
            .select_related("document")
            .order_by("started_at")
        )
        for log in logs:
            payment_meta = (log.meta or {}).get("payment")
            if not payment_meta:
                continue
            document = log.document
            if not document:
                continue
            role = document.creator_role
            doc_meta = document.payment_meta or {}
            if doc_meta.get(role) == payment_meta:
                continue
            doc_meta[role] = payment_meta
            document.payment_meta = doc_meta
            document.save(update_fields=["payment_meta", "updated_at"])
            patched += 1
        self.stdout.write(self.style.SUCCESS(f"Patched {patched} contract payment records."))
