from django.core.management.base import BaseCommand
from django.utils import timezone
from orders.models import Invoice


class Command(BaseCommand):
    help = '만료된 인보이스 상태를 업데이트합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제로 업데이트하지 않고 결과만 출력합니다',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        
        # 만료된 pending 인보이스 찾기
        expired_invoices = Invoice.objects.filter(
            status='pending',
            expires_at__lt=now
        )
        
        count = expired_invoices.count()
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f'[DRY RUN] {count}개의 만료된 인보이스를 찾았습니다.')
            )
            for invoice in expired_invoices:
                self.stdout.write(
                    f'  - {invoice.payment_hash[:16]}... ({invoice.user.username}, {invoice.amount_sats} sats)'
                )
        else:
            # 실제 업데이트
            updated = expired_invoices.update(status='expired')
            
            self.stdout.write(
                self.style.SUCCESS(f'{updated}개의 인보이스 상태를 "만료됨"으로 업데이트했습니다.')
            )
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('만료된 인보이스가 없습니다.')
            ) 