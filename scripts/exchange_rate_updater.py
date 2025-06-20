#!/usr/bin/env python3
"""
SatoShop 환율 업데이트 스크립트
외부 리눅스 서버의 crontab에서 실행하여 웹훅을 호출하는 스크립트
"""

import requests
import json
import logging
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/satoshop_exchange_updater.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ExchangeRateUpdater:
    """환율 업데이트 스크립트"""
    
    def __init__(self):
        # 환경 변수에서 설정 로드
        self.webhook_token = os.getenv('SATOSHOP_WEBHOOK_TOKEN')
        self.webhook_urls = self._load_webhook_urls()
        self.timeout = 30  # 30초 타임아웃
        
        if not self.webhook_token:
            logger.error("SATOSHOP_WEBHOOK_TOKEN 환경 변수가 설정되지 않았습니다.")
            sys.exit(1)
    
    def _load_webhook_urls(self) -> List[str]:
        """웹훅 URL 목록 로드"""
        # 환경 변수에서 URL 목록 가져오기 (쉼표로 구분)
        urls_env = os.getenv('SATOSHOP_WEBHOOK_URLS', '')
        
        if urls_env:
            urls = [url.strip() for url in urls_env.split(',') if url.strip()]
        else:
            # 기본 URL 목록
            urls = [
                'https://satoshop-dev.onrender.com/webhook/update-exchange-rate/',
                'https://satoshop.onrender.com/webhook/update-exchange-rate/',
                'https://store.btcmap.kr/webhook/update-exchange-rate/',
            ]
        
        logger.info(f"웹훅 URL 목록: {len(urls)}개 설정됨")
        return urls
    
    def call_webhook(self, url: str) -> Dict:
        """단일 웹훅 호출"""
        payload = {
            'token': self.webhook_token,
            'source': 'external_cron_server',
            'timestamp': datetime.now().isoformat(),
            'server_info': {
                'hostname': os.uname().nodename,
                'script_version': '1.0.0'
            }
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'SatoShop-ExchangeUpdater/1.0.0'
        }
        
        try:
            logger.info(f"웹훅 호출 시작: {url}")
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            result = {
                'url': url,
                'status_code': response.status_code,
                'success': False,
                'response_data': None,
                'error': None
            }
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    result['success'] = response_data.get('success', False)
                    result['response_data'] = response_data
                    
                    if result['success']:
                        btc_rate = response_data.get('btc_krw_rate', 0)
                        logger.info(f"✅ 성공: {url} - 환율: {btc_rate:,.0f} KRW")
                    else:
                        error_msg = response_data.get('error', 'Unknown error')
                        logger.warning(f"❌ 실패: {url} - {error_msg}")
                        result['error'] = error_msg
                except json.JSONDecodeError:
                    result['error'] = 'Invalid JSON response'
                    logger.error(f"❌ JSON 파싱 실패: {url}")
            else:
                result['error'] = f'HTTP {response.status_code}'
                logger.warning(f"❌ HTTP 오류: {url} - {response.status_code}")
            
            return result
            
        except requests.exceptions.Timeout:
            result = {
                'url': url,
                'status_code': 0,
                'success': False,
                'error': 'Timeout',
                'response_data': None
            }
            logger.error(f"❌ 타임아웃: {url}")
            return result
            
        except requests.exceptions.ConnectionError:
            result = {
                'url': url,
                'status_code': 0,
                'success': False,
                'error': 'Connection failed',
                'response_data': None
            }
            logger.error(f"❌ 연결 실패: {url}")
            return result
            
        except Exception as e:
            result = {
                'url': url,
                'status_code': 0,
                'success': False,
                'error': str(e),
                'response_data': None
            }
            logger.error(f"❌ 예상치 못한 오류: {url} - {e}")
            return result
    
    def update_all_servers(self) -> Dict:
        """모든 서버에 환율 업데이트 요청"""
        logger.info("🚀 환율 업데이트 시작")
        start_time = datetime.now()
        
        results = []
        success_count = 0
        
        for url in self.webhook_urls:
            result = self.call_webhook(url)
            results.append(result)
            
            if result['success']:
                success_count += 1
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        summary = {
            'total_servers': len(self.webhook_urls),
            'success_count': success_count,
            'failure_count': len(self.webhook_urls) - success_count,
            'duration_seconds': duration,
            'results': results,
            'timestamp': end_time.isoformat()
        }
        
        # 결과 로깅
        logger.info(f"📊 최종 결과: {success_count}/{len(self.webhook_urls)} 서버 성공")
        logger.info(f"⏰ 소요 시간: {duration:.2f}초")
        
        # 모든 서버가 실패한 경우에만 실패로 처리
        if success_count == 0:
            logger.error("❌ 모든 서버에서 환율 업데이트 실패!")
            return summary
        else:
            logger.info(f"✅ {success_count}개 서버에서 환율 업데이트 성공!")
            return summary
    
    def run(self) -> bool:
        """메인 실행 함수"""
        try:
            summary = self.update_all_servers()
            
            # 성공 여부 반환 (적어도 하나의 서버가 성공하면 True)
            return summary['success_count'] > 0
            
        except Exception as e:
            logger.error(f"❌ 스크립트 실행 중 오류: {e}", exc_info=True)
            return False

def main():
    """메인 함수"""
    updater = ExchangeRateUpdater()
    success = updater.run()
    
    # crontab에서 실패를 감지할 수 있도록 exit code 설정
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main() 