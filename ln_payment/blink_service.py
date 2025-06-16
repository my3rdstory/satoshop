import os
import json
import requests
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from stores.models import Store

logger = logging.getLogger(__name__)


class BlinkAPIService:
    """Blink API 서비스 클래스"""
    
    def __init__(self, api_key, wallet_id, api_url=None):
        """
        BlinkAPIService 초기화
        
        Args:
            api_key: Blink API 키 (필수)
            wallet_id: Blink 월렛 ID (필수)
            api_url: Blink API URL (선택사항)
        """
        self.api_key = api_key
        self.wallet_id = wallet_id
        self.api_url = api_url or getattr(settings, 'BLINK_API_URL', 'https://api.staging.blink.sv/graphql')
        
        if not self.api_key:
            raise ValueError("Blink API 키가 설정되지 않았습니다.")
        if not self.wallet_id:
            raise ValueError("Blink 월렛 ID가 설정되지 않았습니다.")
        
        if self.api_key and self.wallet_id:
            logger.debug(f"BlinkAPIService 초기화: API URL={self.api_url}, 월렛 ID={self.wallet_id}")
            if settings.DEBUG:
                logger.debug(f"API 키 길이: {len(self.api_key)}, 시작: {self.api_key[:8]}...")
                print(f"DEBUG: BlinkAPIService 초기화")  # 임시 print
                print(f"DEBUG: API URL={self.api_url}")
                print(f"DEBUG: 월렛 ID={self.wallet_id}")
                print(f"DEBUG: API 키 길이={len(self.api_key)}")
                print(f"DEBUG: API 키 시작={self.api_key[:8]}...")
                # API 키 전체 로깅 제거 - 보안 위험
                
                # API 키 형식 분석
                if self.api_key.startswith('blink_'):
                    print(f"DEBUG: ✓ API 키가 'blink_' 접두사로 시작함")
                else:
                    print(f"DEBUG: ⚠️ API 키가 'blink_' 접두사로 시작하지 않음")
                
                # JWT 토큰인지 확인
                parts = self.api_key.split('.')
                if len(parts) == 3:
                    print(f"DEBUG: ⚠️ API 키가 JWT 토큰 형식일 수 있음 (3개 부분)")
                else:
                    print(f"DEBUG: ✓ API 키가 일반 키 형식")
                    
                # 월렛 ID UUID 형식 확인
                try:
                    import uuid
                    uuid.UUID(self.wallet_id)
                    print(f"DEBUG: ✓ 월렛 ID가 올바른 UUID 형식")
                except:
                    print(f"DEBUG: ⚠️ 월렛 ID가 UUID 형식이 아님")
    
    def _make_request(self, query, variables=None):
        """GraphQL 요청 실행"""
        # 여러 가능한 인증 방식 시도
        auth_methods = [
            {'X-API-KEY': self.api_key},  # 잘 동작하는 코드 형식 (대문자 KEY)
            {'X-API-Key': self.api_key},  # 기존 형식
            {'Authorization': f'Bearer {self.api_key}'},
            {'Authorization': f'API-Key {self.api_key}'},
            {'Authorization': self.api_key},
        ]
        
        payload = {
            'query': query,
            'variables': variables or {}
        }
        
        # API 문서에서 권장하는 엔드포인트 사용
        endpoints = [
            'https://api.blink.sv/graphql',  # Production (문서의 기본)
            'https://api.staging.blink.sv/graphql',  # Staging (문서에서 명시)
        ]
        
        if settings.DEBUG:
            print(f"DEBUG: 여러 인증 방식으로 API 키 테스트")
            print(f"DEBUG: API 키: {self.api_key[:20]}...")
        
        # 각 엔드포인트와 인증 방식 조합 시도
        for endpoint in endpoints:
            for auth_method in auth_methods:
                
                headers = {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    **auth_method  # 인증 헤더 병합
                }
                
                if settings.DEBUG:
                    auth_header_display = str(auth_method)
                    print(f"DEBUG: 시도 - {endpoint}")
                    print(f"DEBUG: 인증 헤더: {auth_header_display}")
                
                try:
                    # 먼저 authorization 쿼리로 API 키 유효성 확인
                    auth_test_payload = {
                        'query': 'query { authorization { scopes } }'
                    }
                    
                    auth_response = requests.post(
                        endpoint,
                        headers=headers,
                        json=auth_test_payload,
                        timeout=30
                    )
                    
                    if settings.DEBUG:
                        print(f"DEBUG: 인증 테스트 응답 상태: {auth_response.status_code}")
                        
                    if auth_response.status_code == 200:
                        # authorization 성공시 응답 확인
                        try:
                            auth_data = auth_response.json()
                            if settings.DEBUG:
                                print(f"DEBUG: ✅ 인증 성공!")
                                print(f"DEBUG: 엔드포인트: {endpoint}")
                                print(f"DEBUG: 인증 방식: {auth_method}")
                                print(f"DEBUG: 인증 응답: {auth_data}")
                            
                            # 인증이 성공했으면 실제 쿼리 실행
                            response = requests.post(
                                endpoint,
                                headers=headers,
                                json=payload,
                                timeout=30
                            )
                            
                            if settings.DEBUG:
                                print(f"DEBUG: 실제 쿼리 응답 상태: {response.status_code}")
                                print(f"DEBUG: 실제 쿼리 응답: {response.text}")
                            
                            if not response.ok:
                                return {
                                    'success': False,
                                    'error': f'HTTP 오류: {response.status_code} {response.reason}'
                                }
                            
                            data = response.json()
                            
                            if 'errors' in data:
                                error_messages = [error.get('message', '알 수 없는 오류') for error in data['errors']]
                                return {
                                    'success': False,
                                    'error': f'GraphQL 오류: {", ".join(error_messages)}'
                                }
                            
                            return {
                                'success': True,
                                'data': data.get('data', {})
                            }
                            
                        except json.JSONDecodeError as e:
                            if settings.DEBUG:
                                print(f"DEBUG: 인증 테스트 JSON 파싱 오류: {str(e)}")
                            continue
                            
                    elif auth_response.status_code == 401:
                        if settings.DEBUG:
                            print(f"DEBUG: 401 인증 실패")
                            print(f"DEBUG: 응답 내용: {auth_response.text[:200]}...")
                        continue
                    else:
                        if settings.DEBUG:
                            print(f"DEBUG: 예상치 못한 응답 {auth_response.status_code}: {auth_response.text[:200]}...")
                        continue
                        
                except requests.exceptions.Timeout:
                    if settings.DEBUG:
                        print(f"DEBUG: 타임아웃")
                    continue
                except requests.exceptions.ConnectionError:
                    if settings.DEBUG:
                        print(f"DEBUG: 연결 오류")
                    continue
                except Exception as e:
                    if settings.DEBUG:
                        print(f"DEBUG: 예외 발생: {str(e)}")
                    continue
        
        # 모든 조합에서 실패
        return {
            'success': False,
            'error': '모든 인증 방식에서 API 키 인증에 실패했습니다. API 키가 올바른지 확인해주세요.'
        }
    
    def create_invoice(self, amount_sats, memo='', expires_in_minutes=15):
        """
        Lightning 인보이스 생성
        
        Args:
            amount_sats: 사토시 단위 금액
            memo: 메모 (선택사항)
            expires_in_minutes: 만료 시간 (분)
        
        Returns:
            dict: {
                'success': bool,
                'payment_hash': str,
                'invoice': str,
                'amount_sats': int,
                'expires_at': datetime,
                'error': str (실패시)
            }
        """
        query = """
        mutation LnInvoiceCreate($input: LnInvoiceCreateInput!) {
          lnInvoiceCreate(input: $input) {
            invoice {
              paymentRequest
              paymentHash
              satoshis
              paymentStatus
            }
            errors {
              message
              path
              code
            }
          }
        }
        """
        
        variables = {
            'input': {
                'walletId': self.wallet_id,
                'amount': str(amount_sats),  # 문자열로 변환 (잘 동작하는 코드와 동일)
                'memo': memo,
                'expiresIn': expires_in_minutes * 60  # 초 단위로 추가
            }
        }
        
        # 디버깅: 요청 변수 로깅
        if settings.DEBUG:
            print(f"DEBUG: 인보이스 생성 요청 변수: {variables}")
        
        result = self._make_request(query, variables)
        
        if not result['success']:
            return result
        
        data = result['data']
        
        if 'lnInvoiceCreate' not in data:
            return {
                'success': False,
                'error': '인보이스 생성 응답에 데이터가 없습니다.'
            }
        
        ln_invoice_create = data['lnInvoiceCreate']
        
        if 'errors' in ln_invoice_create and ln_invoice_create['errors']:
            error_messages = [error.get('message', '알 수 없는 오류') for error in ln_invoice_create['errors']]
            return {
                'success': False,
                'error': f'인보이스 생성 오류: {", ".join(error_messages)}'
            }
        
        invoice_data = ln_invoice_create.get('invoice')
        if not invoice_data:
            return {
                'success': False,
                'error': '인보이스 데이터가 없습니다.'
            }
        
        expires_at = timezone.now() + timedelta(minutes=expires_in_minutes)
        
        # 디버깅: 생성된 인보이스 정보 로깅
        if settings.DEBUG:
            print(f"DEBUG: 생성된 인보이스 데이터: {invoice_data}")
            print(f"DEBUG: 인보이스 문자열: {invoice_data['paymentRequest']}")
        
        return {
            'success': True,
            'payment_hash': invoice_data['paymentHash'],
            'invoice': invoice_data['paymentRequest'],
            'amount_sats': invoice_data['satoshis'],
            'expires_at': expires_at
        }
    
    def check_invoice_status(self, payment_hash):
        """
        인보이스 결제 상태 확인
        
        Args:
            payment_hash: 결제 해시
        
        Returns:
            dict: {
                'success': bool,
                'status': str ('pending', 'paid', 'expired'),
                'error': str (실패시)
            }
        """
        query = """
        query LnInvoicePaymentStatusByHash($input: LnInvoicePaymentStatusByHashInput!) {
          lnInvoicePaymentStatusByHash(input: $input) {
            status
            paymentHash
            paymentRequest
          }
        }
        """
        
        variables = {
            'input': {
                'paymentHash': payment_hash
            }
        }
        
        result = self._make_request(query, variables)
        
        if not result['success']:
            return result
        
        data = result['data']
        
        if settings.DEBUG:
            print(f"DEBUG: 결제 상태 확인 전체 응답: {data}")
        
        if 'lnInvoicePaymentStatusByHash' not in data:
            return {
                'success': False,
                'error': '결제 상태 확인 응답에 데이터가 없습니다.'
            }
        
        status_data = data['lnInvoicePaymentStatusByHash']
        
        if settings.DEBUG:
            print(f"DEBUG: 결제 상태 데이터: {status_data}")
        
        raw_status = status_data.get('status', '').upper()
        
        if settings.DEBUG:
            print(f"DEBUG: 원본 상태값: '{raw_status}'")
        
        # Blink API 상태값을 우리 시스템에 맞게 변환
        # 다양한 가능한 상태값들을 모두 처리
        if raw_status in ['PENDING']:
            status = 'pending'
        elif raw_status in ['PAID', 'SETTLED', 'CONFIRMED', 'SUCCESS']:
            status = 'paid'
        elif raw_status in ['EXPIRED', 'FAILED', 'CANCELLED']:
            status = 'expired'
        else:
            # 알 수 없는 상태값이면 로깅하고 pending으로 처리
            if settings.DEBUG:
                print(f"DEBUG: ⚠️ 알 수 없는 상태값: '{raw_status}' - pending으로 처리")
            status = 'pending'
        
        if settings.DEBUG:
            print(f"DEBUG: 변환된 상태: '{status}'")
        
        return {
            'success': True,
            'status': status,
            'raw_status': raw_status,  # 디버깅용으로 원본 상태도 반환
            'payment_hash': status_data.get('paymentHash'),
            'payment_request': status_data.get('paymentRequest')
        }
    
    def get_account_info(self):
        """
        현재 API 키로 접근 가능한 계정 정보와 월렛 목록 조회
        
        Returns:
            dict: {
                'success': bool,
                'account_info': dict,
                'wallets': list,
                'error': str (실패시)
            }
        """
        query = """
        query GetAccountInfo {
          me {
            id
            username
            defaultAccount {
              id
              wallets {
                id
                walletCurrency
                balance
              }
              defaultWallet {
                id
                walletCurrency
              }
            }
          }
        }
        """
        
        result = self._make_request(query)
        
        if not result['success']:
            return result
        
        data = result['data']
        
        if 'me' not in data or not data['me']:
            return {
                'success': False,
                'error': '계정 정보를 가져올 수 없습니다.'
            }
        
        me = data['me']
        account = me.get('defaultAccount', {})
        wallets = account.get('wallets', [])
        default_wallet = account.get('defaultWallet', {})
        
        return {
            'success': True,
            'account_info': {
                'user_id': me.get('id'),
                'username': me.get('username'),
                'account_id': account.get('id'),
                'default_wallet_id': default_wallet.get('id'),
                'default_wallet_currency': default_wallet.get('walletCurrency')
            },
            'wallets': wallets
        }


def get_blink_service_for_store(store):
    """
    스토어에 맞는 BlinkAPIService 인스턴스를 반환
    
    Args:
        store: Store 인스턴스
    
    Returns:
        BlinkAPIService: 스토어 설정으로 초기화된 서비스
    """
    if not store:
        raise ValueError("스토어 정보가 필요합니다.")
    
    try:
        # 스토어에서 API 정보 가져오기
        api_key = store.get_blink_api_info()
        wallet_id = store.get_blink_wallet_id()
        
        if settings.DEBUG:
            logger.debug(f"스토어에서 API 정보 가져옴: API 키 길이={len(api_key) if api_key else 0}, 월렛 ID={wallet_id}")
        
        if not api_key or not wallet_id:
            raise ValueError("스토어에 Blink API 정보가 설정되지 않았습니다.")
        
        return BlinkAPIService(api_key=api_key, wallet_id=wallet_id)
        
    except Exception as e:
        if settings.DEBUG:
            logger.error(f"BlinkAPIService 생성 실패: {str(e)}")
        raise e 