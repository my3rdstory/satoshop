from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Sum, Q
from meetup.models import Meetup, MeetupOrder


class Command(BaseCommand):
    help = '밋업 관련 통계를 확인합니다.'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--store',
            type=str,
            help='특정 스토어의 통계만 보기 (store_id)',
        )
        
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='상세한 밋업별 통계 표시',
        )
        
        parser.add_argument(
            '--export',
            type=str,
            help='결과를 CSV 파일로 내보내기 (파일명)',
        )
    
    def handle(self, *args, **options):
        store_id = options.get('store')
        detailed = options['detailed']
        export_file = options.get('export')
        
        self.stdout.write('=' * 60)
        self.stdout.write('📊 밋업 통계 대시보드')
        self.stdout.write('=' * 60)
        
        # 현재 시간
        now = timezone.now()
        self.stdout.write(f'생성 시간: {now.strftime("%Y-%m-%d %H:%M:%S")}')
        
        # 기본 필터
        meetup_filter = {}
        order_filter = {}
        
        if store_id:
            from stores.models import Store
            try:
                store = Store.objects.get(store_id=store_id)
                meetup_filter['store'] = store
                order_filter['meetup__store'] = store
                self.stdout.write(f'📍 스토어: {store.store_name}')
            except Store.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ 스토어 "{store_id}"를 찾을 수 없습니다.')
                )
                return
        
        self.stdout.write('')
        
        # 1. 전체 통계
        self.stdout.write('🏠 전체 통계')
        self.stdout.write('-' * 40)
        
        total_meetups = Meetup.objects.filter(**meetup_filter).count()
        active_meetups = Meetup.objects.filter(is_active=True, **meetup_filter).count()
        inactive_meetups = total_meetups - active_meetups
        
        self.stdout.write(f'총 밋업 수: {total_meetups:,}개')
        self.stdout.write(f'  - 활성 밋업: {active_meetups:,}개')
        self.stdout.write(f'  - 비활성 밋업: {inactive_meetups:,}개')
        
        # 2. 예약 통계
        self.stdout.write('\n🎫 예약 통계')
        self.stdout.write('-' * 40)
        
        # 전체 주문 통계
        total_orders = MeetupOrder.objects.filter(**order_filter).count()
        confirmed_orders = MeetupOrder.objects.filter(
            status__in=['confirmed', 'completed'], **order_filter
        ).count()
        pending_orders = MeetupOrder.objects.filter(
            status='pending', **order_filter
        ).count()
        cancelled_orders = MeetupOrder.objects.filter(
            status='cancelled', **order_filter
        ).count()
        
        self.stdout.write(f'총 주문 수: {total_orders:,}개')
        self.stdout.write(f'  - 확정: {confirmed_orders:,}개 ({confirmed_orders/total_orders*100:.1f}%)' if total_orders > 0 else '  - 확정: 0개')
        self.stdout.write(f'  - 대기: {pending_orders:,}개 ({pending_orders/total_orders*100:.1f}%)' if total_orders > 0 else '  - 대기: 0개')
        self.stdout.write(f'  - 취소: {cancelled_orders:,}개 ({cancelled_orders/total_orders*100:.1f}%)' if total_orders > 0 else '  - 취소: 0개')
        
        # 임시 예약 세부 통계
        active_temp_reservations = MeetupOrder.objects.filter(
            status='pending',
            is_temporary_reserved=True,
            reservation_expires_at__gt=now,
            **order_filter
        ).count()
        
        expired_temp_reservations = MeetupOrder.objects.filter(
            status='pending',
            is_temporary_reserved=True,
            reservation_expires_at__lt=now,
            **order_filter
        ).count()
        
        self.stdout.write(f'\n⏳ 임시 예약 상태:')
        self.stdout.write(f'  - 활성 임시 예약: {active_temp_reservations:,}개')
        self.stdout.write(f'  - 만료된 임시 예약: {expired_temp_reservations:,}개')
        
        # 3. 매출 통계
        self.stdout.write('\n💰 매출 통계')
        self.stdout.write('-' * 40)
        
        total_revenue = MeetupOrder.objects.filter(
            status__in=['confirmed', 'completed'], **order_filter
        ).aggregate(
            total=Sum('total_price')
        )['total'] or 0
        
        avg_price = total_revenue / confirmed_orders if confirmed_orders > 0 else 0
        
        self.stdout.write(f'총 매출: {total_revenue:,} sats')
        self.stdout.write(f'평균 참가비: {avg_price:.0f} sats')
        
        # 4. 정원 및 참석 통계
        self.stdout.write('\n👥 참가자 통계')
        self.stdout.write('-' * 40)
        
        # 참석률
        attended_count = MeetupOrder.objects.filter(
            status__in=['confirmed', 'completed'],
            attended=True,
            **order_filter
        ).count()
        
        attendance_rate = (attended_count / confirmed_orders * 100) if confirmed_orders > 0 else 0
        
        self.stdout.write(f'총 참가자: {confirmed_orders:,}명')
        self.stdout.write(f'실제 참석자: {attended_count:,}명')
        self.stdout.write(f'참석률: {attendance_rate:.1f}%')
        
        # 5. 정원 마감 통계
        meetups_with_limit = Meetup.objects.filter(
            max_participants__isnull=False, **meetup_filter
        )
        
        full_meetups = [m for m in meetups_with_limit if m.is_full]
        
        self.stdout.write(f'\n🎯 정원 관리:')
        self.stdout.write(f'  - 정원 제한 밋업: {meetups_with_limit.count():,}개')
        self.stdout.write(f'  - 정원 마감 밋업: {len(full_meetups):,}개')
        
        # 상세 통계 (옵션)
        if detailed:
            self.stdout.write('\n📋 밋업별 상세 통계')
            self.stdout.write('=' * 60)
            
            meetups = Meetup.objects.filter(**meetup_filter).prefetch_related('orders')
            
            for meetup in meetups:
                self.stdout.write(f'\n🎪 {meetup.name} ({meetup.store.store_name})')
                self.stdout.write('-' * 50)
                
                orders = meetup.orders.all()
                confirmed = orders.filter(status__in=['confirmed', 'completed']).count()
                pending = orders.filter(status='pending').count()
                cancelled = orders.filter(status='cancelled').count()
                attended = orders.filter(attended=True).count()
                
                revenue = orders.filter(status__in=['confirmed', 'completed']).aggregate(
                    total=Sum('total_price')
                )['total'] or 0
                
                self.stdout.write(f'  참가자: {confirmed}/{meetup.max_participants or "무제한"}')
                self.stdout.write(f'  대기/취소: {pending}/{cancelled}')
                self.stdout.write(f'  참석률: {(attended/confirmed*100):.1f}%' if confirmed > 0 else '  참석률: -')
                self.stdout.write(f'  매출: {revenue:,} sats')
                
                if meetup.max_participants and meetup.is_full:
                    self.stdout.write('  🔴 정원 마감')
                
        # CSV 내보내기 (옵션)
        if export_file:
            self.export_to_csv(export_file, meetup_filter, order_filter)
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('✨ 통계 조회 완료')
        self.stdout.write('=' * 60)
    
    def export_to_csv(self, filename, meetup_filter, order_filter):
        """통계를 CSV 파일로 내보내기"""
        import csv
        from datetime import datetime
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                
                # 헤더
                writer.writerow([
                    '밋업명', '스토어', '상태', '최대정원', '확정참가자', '대기중', '취소된주문',
                    '참석자', '참석률(%)', '총매출(sats)', '평균참가비(sats)', '생성일'
                ])
                
                # 데이터
                meetups = Meetup.objects.filter(**meetup_filter).prefetch_related('orders')
                
                for meetup in meetups:
                    orders = meetup.orders.all()
                    confirmed = orders.filter(status__in=['confirmed', 'completed']).count()
                    pending = orders.filter(status='pending').count()
                    cancelled = orders.filter(status='cancelled').count()
                    attended = orders.filter(attended=True).count()
                    
                    revenue = orders.filter(status__in=['confirmed', 'completed']).aggregate(
                        total=Sum('total_price')
                    )['total'] or 0
                    
                    avg_price = revenue / confirmed if confirmed > 0 else 0
                    attendance_rate = (attended / confirmed * 100) if confirmed > 0 else 0
                    
                    writer.writerow([
                        meetup.name,
                        meetup.store.store_name,
                        '활성' if meetup.is_active else '비활성',
                        meetup.max_participants or '무제한',
                        confirmed,
                        pending,
                        cancelled,
                        attended,
                        f'{attendance_rate:.1f}',
                        revenue,
                        f'{avg_price:.0f}',
                        meetup.created_at.strftime('%Y-%m-%d')
                    ])
            
            self.stdout.write(
                self.style.SUCCESS(f'📁 통계가 {filename} 파일로 내보내졌습니다.')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ CSV 내보내기 실패: {str(e)}')
            ) 