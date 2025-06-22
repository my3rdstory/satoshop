from django.core.management.base import BaseCommand
from django.utils import timezone
from myshop.models import SiteSettings, ExchangeRate
from myshop.services import TelegramService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '텔레그램 봇 연결 및 환율 알림 기능을 테스트합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='텔레그램 봇 연결만 테스트합니다',
        )
        parser.add_argument(
            '--send-test-message',
            action='store_true',
            help='테스트 메시지를 전송합니다',
        )
        parser.add_argument(
            '--send-rate-update',
            action='store_true',
            help='현재 환율 정보로 알림 메시지를 전송합니다',
        )
        parser.add_argument(
            '--bot-token',
            type=str,
            help='테스트할 봇 토큰 (기본값: 사이트 설정의 봇 토큰)',
        )
        parser.add_argument(
            '--chat-id',
            type=str,
            help='테스트할 채팅 ID (기본값: 사이트 설정의 채팅 ID)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🤖 텔레그램 봇 테스트 시작'))
        
        # 설정 로드
        site_settings = SiteSettings.get_settings()
        
        # 봇 토큰과 채팅 ID 결정
        bot_token = options.get('bot_token') or site_settings.telegram_bot_token
        chat_id = options.get('chat_id') or site_settings.telegram_chat_id
        
        if not bot_token:
            self.stdout.write(
                self.style.ERROR('❌ 텔레그램 봇 토큰이 설정되지 않았습니다.')
            )
            self.stdout.write('사이트 설정에서 telegram_bot_token을 설정하거나 --bot-token 옵션을 사용하세요.')
            return
        
        if not chat_id:
            self.stdout.write(
                self.style.ERROR('❌ 텔레그램 채팅 ID가 설정되지 않았습니다.')
            )
            self.stdout.write('사이트 설정에서 telegram_chat_id를 설정하거나 --chat-id 옵션을 사용하세요.')
            return
        
        # 연결 테스트
        if options['test_connection']:
            self.test_bot_connection(bot_token)
        
        # 테스트 메시지 전송
        if options['send_test_message']:
            self.send_test_message(bot_token, chat_id)
        
        # 환율 업데이트 메시지 전송
        if options['send_rate_update']:
            self.send_rate_update_message(bot_token, chat_id)
        
        # 옵션이 없으면 전체 테스트 실행
        if not any([options['test_connection'], options['send_test_message'], options['send_rate_update']]):
            self.test_bot_connection(bot_token)
            self.send_test_message(bot_token, chat_id)
            self.send_rate_update_message(bot_token, chat_id)

    def test_bot_connection(self, bot_token):
        """텔레그램 봇 연결 테스트"""
        self.stdout.write('🔌 텔레그램 봇 연결 테스트 중...')
        
        result = TelegramService.test_bot_connection(bot_token)
        
        if result['success']:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ 봇 연결 성공: {result["bot_name"]} (@{result["bot_username"]})'
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'❌ 봇 연결 실패: {result["error"]}')
            )

    def send_test_message(self, bot_token, chat_id):
        """테스트 메시지 전송"""
        self.stdout.write('📤 테스트 메시지 전송 중...')
        
        current_time = timezone.now()
        message = f"""🧪 *Satoshop 텔레그램 봇 테스트*

✅ 텔레그램 봇이 정상적으로 작동하고 있습니다!

⏰ 테스트 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}
🤖 봇 상태: 정상 연결됨
📡 메시지 전송: 성공

이 메시지는 텔레그램 봇 기능 테스트용입니다."""
        
        success = TelegramService.send_message(bot_token, chat_id, message)
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(f'✅ 테스트 메시지 전송 성공: {chat_id}')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'❌ 테스트 메시지 전송 실패: {chat_id}')
            )

    def send_rate_update_message(self, bot_token, chat_id):
        """현재 환율 정보로 알림 메시지 전송"""
        self.stdout.write('💰 환율 알림 메시지 전송 중...')
        
        # 최신 환율 데이터 가져오기
        latest_rate = ExchangeRate.get_latest_rate()
        
        if not latest_rate:
            self.stdout.write(
                self.style.WARNING('⚠️ 환율 데이터가 없습니다. 먼저 환율을 업데이트하세요.')
            )
            return
        
        # 이전 환율과 비교
        previous_rate = ExchangeRate.objects.filter(
            created_at__lt=latest_rate.created_at
        ).order_by('-created_at').first()
        
        current_time = timezone.now()
        korea_time = latest_rate.created_at.astimezone(timezone.get_current_timezone())
        
        if previous_rate:
            rate_change = float(latest_rate.btc_krw_rate) - float(previous_rate.btc_krw_rate)
            rate_change_percent = (rate_change / float(previous_rate.btc_krw_rate)) * 100
            
            if rate_change > 0:
                change_emoji = "📈"
                change_text = f"상승 (+{rate_change:,.0f} KRW, +{rate_change_percent:.2f}%)"
            elif rate_change < 0:
                change_emoji = "📉"
                change_text = f"하락 ({rate_change:,.0f} KRW, {rate_change_percent:.2f}%)"
            else:
                change_emoji = "➡️"
                change_text = "보합 (변화없음)"
        else:
            change_emoji = "🆕"
            change_text = "첫 번째 환율 데이터"
        
        message = f"""🪙 *환율 업데이트 알림 (테스트)*

{change_emoji} *BTC/KRW: `{latest_rate.btc_krw_rate:,} KRW`*

📊 변동: {change_text}
⏰ 업데이트: {korea_time.strftime('%m/%d %H:%M:%S')}
💡 소스: 업비트 API

🧪 이 메시지는 텔레그램 봇 테스트용입니다."""
        
        success = TelegramService.send_message(bot_token, chat_id, message)
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(f'✅ 환율 알림 메시지 전송 성공: {chat_id}')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'❌ 환율 알림 메시지 전송 실패: {chat_id}')
            ) 