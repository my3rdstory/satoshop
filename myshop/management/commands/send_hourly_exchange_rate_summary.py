from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from myshop.models import ExchangeRate, SiteSettings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '최근 1시간 내 환율 데이터를 요약하여 이메일로 전송합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='데이터가 없어도 강제로 이메일을 전송합니다',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='테스트용 이메일 주소 (기본값: 사이트 설정의 알림 이메일)',
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=1,
            help='조회할 시간 범위 (기본값: 1시간)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='포함할 최대 환율 데이터 개수 (기본값: 5개)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('📊 환율 요약 이메일 전송 시작'))
        
        # 설정값 가져오기
        hours_back = options['hours']
        limit = options['limit']
        force = options['force']
        
        # 이메일 주소 결정
        if options.get('email'):
            notification_email = options['email']
        else:
            site_settings = SiteSettings.get_settings()
            notification_email = site_settings.exchange_rate_notification_email
        
        # 최근 지정된 시간 내의 환율 데이터 조회
        cutoff_time = timezone.now() - timedelta(hours=hours_back)
        recent_rates = ExchangeRate.objects.filter(
            created_at__gte=cutoff_time
        ).order_by('-created_at')[:limit]
        
        if not recent_rates and not force:
            self.stdout.write(
                self.style.WARNING(f'⚠️  최근 {hours_back}시간 내 환율 데이터가 없습니다. --force 옵션으로 강제 전송 가능합니다.')
            )
            return
        
        # 이메일 전송
        try:
            self.send_summary_email(notification_email, recent_rates, hours_back, limit)
            self.stdout.write(
                self.style.SUCCESS(f'✅ 환율 요약 이메일 전송 성공: {notification_email}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'📈 포함된 환율 데이터: {len(recent_rates)}개')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 환율 요약 이메일 전송 실패: {str(e)}')
            )

    def send_summary_email(self, email, rates, hours_back, limit):
        """환율 요약 이메일 전송"""
        current_time = timezone.now()
        
        # 제목 생성
        if rates:
            subject = f'[Satoshop] 환율 요약 리포트 - {current_time.strftime("%Y-%m-%d %H시")}'
        else:
            subject = f'[Satoshop] 환율 요약 리포트 (데이터 없음) - {current_time.strftime("%Y-%m-%d %H시")}'
        
                 # 메시지 내용 생성
        if rates:
            # 환율 데이터가 있는 경우
            latest_rate = rates[0]
            oldest_rate = rates[len(rates)-1] if len(rates) > 1 else latest_rate
            
            # 환율 변화 계산
            if len(rates) > 1:
                rate_change = float(latest_rate.btc_krw_rate) - float(oldest_rate.btc_krw_rate)
                rate_change_percent = (rate_change / float(oldest_rate.btc_krw_rate)) * 100
                
                if rate_change > 0:
                    change_indicator = "📈 상승"
                    change_color = "🟢"
                elif rate_change < 0:
                    change_indicator = "📉 하락"
                    change_color = "🔴"
                else:
                    change_indicator = "➡️ 보합"
                    change_color = "🟡"
            else:
                rate_change = 0
                rate_change_percent = 0
                change_indicator = "➡️ 변화없음"
                change_color = "🟡"
            
            # 환율 데이터 목록 생성 (실제 저장 시간 기준)
            rate_list = []
            for i, rate in enumerate(rates, 1):
                # 한국 시간으로 변환하여 표시
                korea_time = rate.created_at.astimezone(timezone.get_current_timezone())
                rate_list.append(
                    f"{i}. {rate.btc_krw_rate:,} KRW ({korea_time.strftime('%m/%d %H:%M:%S')})"
                )
            
            # 실제 환율 데이터 저장 시간을 기준으로 조회 기간 표시
            oldest_korea_time = oldest_rate.created_at.astimezone(timezone.get_current_timezone())
            latest_korea_time = latest_rate.created_at.astimezone(timezone.get_current_timezone())
            
            message = f"""
안녕하세요, Satoshop 관리자님!

최근 {hours_back}시간 동안의 환율 변동 요약을 보내드립니다.

📊 환율 요약 정보:
• 조회 기간: {oldest_korea_time.strftime('%Y-%m-%d %H:%M')} ~ {latest_korea_time.strftime('%Y-%m-%d %H:%M')} (실제 환율 저장 시간 기준)
• 데이터 개수: {len(rates)}개
• 최신 환율: {latest_rate.btc_krw_rate:,} KRW ({latest_korea_time.strftime('%m/%d %H:%M')})
• 변동 상황: {change_color} {change_indicator}

📈 환율 변화:
• 변동 금액: {rate_change:+,.0f} KRW
• 변동률: {rate_change_percent:+.2f}%

📋 최근 환율 데이터 ({limit}개):
{chr(10).join(rate_list)}

💡 데이터 소스: 업비트 API
⏰ 리포트 생성 시간: {current_time.strftime('%Y년 %m월 %d일 %H시 %M분')}

---
이 메일은 1시간마다 자동으로 발송되는 환율 요약 리포트입니다.
Satoshop 시스템에서 발송됨
            """.strip()
            
        else:
            # 환율 데이터가 없는 경우
            message = f"""
안녕하세요, Satoshop 관리자님!

최근 {hours_back}시간 동안 새로운 환율 데이터가 없습니다.

⚠️ 상황 요약:
• 조회 기간: 최근 {hours_back}시간
• 데이터 개수: 0개
• 상태: 환율 업데이트 없음

🔍 확인 사항:
• 환율 업데이트 스케줄러가 정상 작동하는지 확인해주세요
• 업비트 API 연결 상태를 점검해주세요
• 서버 상태 및 네트워크 연결을 확인해주세요

⏰ 리포트 생성 시간: {current_time.strftime('%Y년 %m월 %d일 %H시 %M분')}

---
이 메일은 1시간마다 자동으로 발송되는 환율 요약 리포트입니다.
Satoshop 시스템에서 발송됨
            """.strip()
        
        # 이메일 전송
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        
        logger.info(f"환율 요약 이메일 전송 성공: {email} - 데이터 {len(rates)}개") 