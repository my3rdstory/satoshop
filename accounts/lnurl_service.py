"""
LNURL-auth 서비스 모듈
라이트닝 네트워크 표준 인증 프로토콜 구현 (lnauth-django 기반)
"""

import os
import binascii
import hashlib
import hmac
from urllib.parse import urlencode
from django.conf import settings
from django.urls import reverse
from django.core.cache import cache
from django.contrib.auth.models import User
import bech32
from secp256k1 import PublicKey

from .models import LightningUser


class LNURLAuthException(Exception):
    """LNURL-auth 관련 예외"""
    pass


class InvalidSigException(LNURLAuthException):
    """잘못된 서명 예외"""
    pass


class LNURLAuthService:
    """LNURL-auth 서비스 (lnauth-django 호환)"""
    
    def __init__(self, domain=None):
        self.domain = domain or getattr(settings, 'LNURL_AUTH_ROOT_DOMAIN', 'localhost:8000')
        # ngrok이나 외부 도메인을 사용할 때는 항상 https 사용
        if 'ngrok' in self.domain or 'localhost' not in self.domain:
            self.protocol = 'https'
        else:
            self.protocol = 'https' if not settings.DEBUG else 'http'
    
    def generate_k1(self):
        """32바이트 k1 챌린지 생성"""
        return os.urandom(32)
    
    def get_auth_url(self, k1_bytes, action='login'):
        """LNURL-auth URL 생성 (bech32 인코딩)"""
        import logging
        logger = logging.getLogger(__name__)
        
        # 콜백 URL 생성
        reverse_url = reverse('accounts:lnurl_auth_callback')
        callback_url = f"{self.protocol}://{self.domain}{reverse_url}"
        
        # k1을 hex로 변환
        k1_hex = k1_bytes.hex()
        
        # 캐시에 k1 저장 (만료 시간 설정)
        timeout = getattr(settings, 'LNURL_AUTH_K1_TIMEOUT', 60 * 60)  # 1시간
        cache.set(f"lnauth-k1-{k1_hex}:{action}", action, timeout=timeout)
        
        # 파라미터와 함께 완전한 URL 생성
        url = f"{callback_url}?tag=login&k1={k1_hex}&action={action}"
        logger.info(f"생성된 콜백 URL: {url}")
        
        # bech32 인코딩
        try:
            data_part = bech32.convertbits(url.encode('utf-8'), 8, 5)
            if data_part is None:
                raise LNURLAuthException("bech32 변환 실패")
            
            bech32_url = bech32.bech32_encode('lnurl', data_part)
            if bech32_url is None:
                raise LNURLAuthException("bech32 인코딩 실패")
            
            final_lnurl = bech32_url.upper()  # LNURL은 대문자로
            logger.info(f"생성된 LNURL: {final_lnurl}")
            logger.info(f"LNURL 길이: {len(final_lnurl)}")
            
            return final_lnurl
            
        except Exception as e:
            logger.error(f"LNURL 생성 실패: {str(e)}")
            raise LNURLAuthException(f"LNURL 생성 실패: {str(e)}")
    
    def verify_ln_auth(self, k1_hex, sig_hex, linking_key_hex, action='login'):
        """LNURL-auth 서명 검증"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"서명 검증 시작: k1={k1_hex[:16]}..., action={action}")
        
        try:
            # hex 문자열을 바이트로 변환
            k1_bytes = binascii.unhexlify(k1_hex)
            sig_bytes = binascii.unhexlify(sig_hex)
            linking_key_bytes = binascii.unhexlify(linking_key_hex)
            logger.info("hex 문자열 변환 성공")
        except binascii.Error as e:
            logger.error(f"hex 변환 실패: {e}")
            raise LNURLAuthException("잘못된 hex 형식")
        
        # 캐시에서 k1 확인 및 제거 (일회용)
        cache_key = f"lnauth-k1-{k1_hex}:{action}"
        logger.info(f"캐시 키 확인: {cache_key}")
        
        if not cache.delete(cache_key):
            logger.error(f"캐시에서 k1 찾을 수 없음: {cache_key}")
            raise LNURLAuthException("k1이 존재하지 않거나 만료됨")
        
        logger.info("캐시에서 k1 삭제 성공")
        
        # secp256k1으로 서명 검증
        try:
            # 공개키 객체 생성
            linking_key_pubkey = PublicKey(linking_key_bytes, raw=True)
            logger.info("공개키 객체 생성 성공")
            
            # 서명 디시리얼라이즈
            sig_raw = linking_key_pubkey.ecdsa_deserialize(sig_bytes)
            logger.info("서명 디시리얼라이즈 성공")
            
            # 서명 검증
            if not linking_key_pubkey.ecdsa_verify(k1_bytes, sig_raw, raw=True):
                logger.error("서명 검증 실패")
                raise InvalidSigException("서명 검증 실패")
            
            logger.info("서명 검증 성공")
                
        except Exception as e:
            if isinstance(e, InvalidSigException):
                raise
            logger.error(f"서명 검증 중 예외: {e}")
            raise LNURLAuthException(f"서명 검증 중 오류: {str(e)}")
    
    def create_lnurl_response(self, k1_hex):
        """LNURL-auth 1단계 응답 생성"""
        callback_url = f"{self.protocol}://{self.domain}" + reverse('accounts:lnurl_auth_callback')
        
        return {
            "tag": "login",
            "k1": k1_hex,
            "callback": callback_url
        }
    
    def authenticate_user(self, linking_key_hex, action='login', k1_hex=None):
        """사용자 인증 또는 등록"""
        if action == 'login':
            return self._login_user(linking_key_hex)
        elif action == 'register':
            return self._register_user(linking_key_hex)
        elif action == 'link':
            return self._link_user(linking_key_hex, k1_hex)
        else:
            raise LNURLAuthException(f"지원하지 않는 액션: {action}")
    
    def _login_user(self, linking_key_hex):
        """기존 사용자 로그인 또는 자동 회원가입"""
        try:
            lightning_user = LightningUser.objects.get(public_key=linking_key_hex)
            lightning_user.update_last_login()
            return lightning_user.user, False  # 기존 사용자
        except LightningUser.DoesNotExist:
            # 등록되지 않은 키면 자동으로 회원가입 처리
            return self._register_user(linking_key_hex)
    
    def _register_user(self, linking_key_hex):
        """새 사용자 등록"""
        # 이미 등록된 키인지 확인
        if LightningUser.objects.filter(public_key=linking_key_hex).exists():
            raise LNURLAuthException("이미 등록된 라이트닝 키입니다.")
        
        # 친근한 사용자명 생성
        username = self._generate_friendly_username(linking_key_hex)
        
        user = User.objects.create_user(
            username=username,
            password=None  # 패스워드 없음
        )
        
        lightning_user = LightningUser.objects.create(
            user=user,
            public_key=linking_key_hex
        )
        lightning_user.update_last_login()
        
        return user, True  # 새 사용자
    
    def _link_user(self, linking_key_hex, k1_hex):
        """기존 사용자에게 라이트닝 지갑 연동"""
        from django.core.cache import cache
        from django.contrib.auth.models import User
        
        if not k1_hex:
            raise LNURLAuthException("k1이 필요합니다.")
        
        # 캐시에서 사용자 ID 확인
        cache_key = f"lnauth-link-user-{k1_hex}"
        user_id = cache.get(cache_key)
        if not user_id:
            raise LNURLAuthException("연동 세션이 만료되었거나 존재하지 않습니다.")
        
        # 사용자 조회
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise LNURLAuthException("사용자를 찾을 수 없습니다.")
        
        # 이미 등록된 키인지 확인
        if LightningUser.objects.filter(public_key=linking_key_hex).exists():
            # 사용자별 에러 캐시에도 저장
            user_error_cache_key = f"lnauth-link-error-user-{user_id}"
            cache.set(user_error_cache_key, "이미 다른 계정에 등록된 라이트닝 키입니다.", timeout=300)
            raise LNURLAuthException("이미 다른 계정에 등록된 라이트닝 키입니다.")
        
        # 이미 다른 라이트닝 지갑이 연동되어 있는지 확인
        if LightningUser.objects.filter(user=user).exists():
            # 사용자별 에러 캐시에도 저장
            user_error_cache_key = f"lnauth-link-error-user-{user_id}"
            cache.set(user_error_cache_key, "이미 다른 라이트닝 지갑이 연동되어 있습니다.", timeout=300)
            raise LNURLAuthException("이미 다른 라이트닝 지갑이 연동되어 있습니다.")
        
        # 라이트닝 지갑 연동
        lightning_user = LightningUser.objects.create(
            user=user,
            public_key=linking_key_hex
        )
        lightning_user.update_last_login()
        
        # 캐시에서 제거
        cache.delete(cache_key)
        
        return user, False  # 기존 사용자, 연동 완료

    def _generate_friendly_username(self, linking_key_hex):
        """친근한 사용자명 생성 (ln_ 접두사 포함)"""
        import random
        import hashlib
        
        # 공개키 앞 16자를 사용자명으로 사용 (기존 방식과 일관성 유지)
        base_username = f"ln_{linking_key_hex[:16]}"
        username = base_username
        counter = 1
        
        # 중복 확인 및 번호 추가
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
            
        return username


def decode_lnurl(lnurl):
    """LNURL을 URL로 디코딩"""
    try:
        if not lnurl.lower().startswith('lnurl'):
            return None
            
        # bech32 디코딩
        hrp, data = bech32.bech32_decode(lnurl.lower())
        if hrp != 'lnurl' or data is None:
            return None
        
        # 5bit에서 8bit로 변환
        decoded_bytes = bech32.convertbits(data, 5, 8, False)
        if decoded_bytes is None:
            return None
            
        return bytes(decoded_bytes).decode('utf-8')
        
    except Exception:
        return None 