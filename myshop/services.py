import requests
import logging
from decimal import Decimal
from django.utils import timezone
from .models import ExchangeRate, SiteSettings

logger = logging.getLogger(__name__)

class TelegramService:
    """텔레그램 봇 서비스"""
    
    @classmethod
    def send_message(cls, bot_token, chat_id, message, parse_mode='Markdown'):
        """텔레그램 메시지 전송"""
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                logger.info(f"텔레그램 메시지 전송 성공: {chat_id}")
                return True
            else:
                logger.error(f"텔레그램 API 오류: {result.get('description', 'Unknown error')}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"텔레그램 메시지 전송 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"텔레그램 메시지 전송 중 오류: {e}")
            return False
    
    @classmethod
    def test_bot_connection(cls, bot_token):
        """텔레그램 봇 연결 테스트"""
        try:
            url = f"https://api.telegram.org/bot{bot_token}/getMe"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                bot_info = result.get('result', {})
                return {
                    'success': True,
                    'bot_name': bot_info.get('first_name', 'Unknown'),
                    'bot_username': bot_info.get('username', 'Unknown')
                }
            else:
                return {
                    'success': False,
                    'error': result.get('description', 'Unknown error')
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

class UpbitExchangeService:
    """업비트 환율 서비스"""
    
    UPBIT_API_URL = "https://api.upbit.com/v1/ticker"
    # 환율 API - 한국은행 공공데이터나 ExchangeRate-API 사용
    USD_KRW_API_URL = "https://api.exchangerate-api.com/v4/latest/USD"
    
    @classmethod
    def fetch_usd_krw_rate(cls):
        """USD/KRW 환율 가져오기"""
        try:
            response = requests.get(cls.USD_KRW_API_URL, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            usd_krw_rate = data.get('rates', {}).get('KRW')
            
            if usd_krw_rate:
                logger.info(f"USD/KRW 환율: 1 USD = {usd_krw_rate} KRW")
                return float(usd_krw_rate)
            else:
                logger.error("USD/KRW 환율 데이터를 찾을 수 없습니다.")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"USD/KRW 환율 API 호출 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"USD/KRW 환율 처리 중 오류: {e}")
            return None
    
    @classmethod
    def fetch_btc_krw_rate(cls):
        """업비트 API에서 BTC/KRW 환율 가져오기 (달러 정보 포함)"""
        try:
            # BTC/KRW 환율 가져오기
            response = requests.get(
                cls.UPBIT_API_URL,
                params={'markets': 'KRW-BTC'},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 0:
                btc_data = data[0]
                trade_price = btc_data.get('trade_price')
                
                if trade_price:
                    # USD/KRW 환율 가져오기
                    usd_krw_rate = cls.fetch_usd_krw_rate()
                    
                    # API 응답 데이터에 달러 정보 추가
                    enhanced_api_data = btc_data.copy()
                    btc_usd_price = None
                    
                    if usd_krw_rate:
                        btc_usd_price = trade_price / usd_krw_rate
                        enhanced_api_data['usd_krw_rate'] = usd_krw_rate
                        enhanced_api_data['btc_usd_price'] = btc_usd_price
                        logger.info(f"BTC/USD 가격: ${btc_usd_price:,.2f}")
                    
                    # 환율 데이터 저장 (달러 정보를 별도 필드에 저장)
                    exchange_rate = ExchangeRate.objects.create(
                        btc_krw_rate=Decimal(str(trade_price)),
                        usd_krw_rate=Decimal(str(usd_krw_rate)) if usd_krw_rate else None,
                        btc_usd_price=Decimal(str(btc_usd_price)) if btc_usd_price else None,
                        api_response_data=enhanced_api_data
                    )
                    
                    # 오래된 데이터 정리 (최근 10개만 유지)
                    ExchangeRate.cleanup_old_rates()
                    
                    logger.info(f"환율 업데이트 성공: 1 BTC = {trade_price:,} KRW")
                    return exchange_rate
                else:
                    logger.error("업비트 API 응답에서 trade_price를 찾을 수 없습니다.")
                    return None
            else:
                logger.error("업비트 API 응답이 비어있습니다.")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"업비트 API 호출 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"환율 데이터 처리 중 오류: {e}")
            return None
    
    @classmethod
    def get_current_rate(cls):
        """현재 환율 가져오기 (DB에서만 조회, 외부 서버에서 crontab으로 업데이트됨)"""
        # 최신 환율 데이터 반환
        latest_rate = ExchangeRate.get_latest_rate()
        if latest_rate:
            return latest_rate
        
        # 환율 데이터가 없으면 API에서 가져오기 시도 (초기 설정용)
        logger.warning("환율 데이터가 없습니다. API에서 가져오는 중...")
        return cls.fetch_btc_krw_rate()
    
    @classmethod
    def convert_krw_to_sats(cls, krw_amount):
        """원화를 사토시로 변환"""
        if not krw_amount or krw_amount <= 0:
            return 0
        
        rate = cls.get_current_rate()
        if rate:
            return rate.get_sats_from_krw(krw_amount)
        
        logger.error("환율 데이터를 가져올 수 없어 변환에 실패했습니다.")
        return 0
    
    @classmethod
    def convert_sats_to_krw(cls, sats_amount):
        """사토시를 원화로 변환"""
        if not sats_amount or sats_amount <= 0:
            return 0
        
        rate = cls.get_current_rate()
        if rate:
            return rate.get_krw_from_sats(sats_amount)
        
        logger.error("환율 데이터를 가져올 수 없어 변환에 실패했습니다.")
        return 0

 