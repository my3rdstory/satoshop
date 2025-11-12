"""
핫링크 보호 기능 테스트 명령어
"""

import requests
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = '핫링크 보호 기능을 테스트합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--image-url',
            type=str,
            help='테스트할 이미지 URL (예: /media/s3/stores/test/image.jpg)',
            default='/media/s3/test-image.jpg'
        )
        parser.add_argument(
            '--base-url',
            type=str,
            help='서버 기본 URL',
            default='http://localhost:8011'
        )

    def handle(self, *args, **options):
        image_url = options['image_url']
        base_url = options['base_url']
        full_url = f"{base_url}{image_url}"
        
        self.stdout.write(
            self.style.SUCCESS(f'핫링크 보호 기능 테스트 시작: {full_url}')
        )
        
        # 테스트 케이스들
        test_cases = [
            {
                'name': '1. Referer 없음 (직접 접근)',
                'headers': {},
                'expected': '허용됨'
            },
            {
                'name': '2. 허용된 도메인 (localhost)',
                'headers': {'Referer': 'http://localhost:8011/'},
                'expected': '허용됨'
            },
            {
                'name': '3. 허용된 도메인 (127.0.0.1)',
                'headers': {'Referer': 'http://127.0.0.1:8011/'},
                'expected': '허용됨'
            },
            {
                'name': '4. 외부 도메인 (차단되어야 함)',
                'headers': {'Referer': 'http://external-site.com/'},
                'expected': '차단됨'
            },
            {
                'name': '5. 다른 외부 도메인 (차단되어야 함)',
                'headers': {'Referer': 'https://evil-site.com/steal-images'},
                'expected': '차단됨'
            }
        ]
        
        for test_case in test_cases:
            self.stdout.write(f"\n{test_case['name']}")
            self.stdout.write(f"Referer: {test_case['headers'].get('Referer', '없음')}")
            
            try:
                response = requests.get(full_url, headers=test_case['headers'], timeout=10)
                
                if response.status_code == 200:
                    result = "✅ 허용됨"
                    content_type = response.headers.get('Content-Type', 'unknown')
                    content_length = len(response.content)
                    self.stdout.write(f"결과: {result} (Content-Type: {content_type}, Size: {content_length} bytes)")
                elif response.status_code == 403:
                    result = "🚫 차단됨"
                    self.stdout.write(f"결과: {result} - {response.text[:100]}")
                elif response.status_code == 404:
                    result = "❓ 파일 없음"
                    self.stdout.write(f"결과: {result} - 테스트 이미지가 존재하지 않습니다")
                else:
                    result = f"❓ 예상치 못한 응답 ({response.status_code})"
                    self.stdout.write(f"결과: {result}")
                
                # 예상 결과와 비교
                if test_case['expected'] == '허용됨' and response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS("✓ 예상대로 작동"))
                elif test_case['expected'] == '차단됨' and response.status_code == 403:
                    self.stdout.write(self.style.SUCCESS("✓ 예상대로 작동"))
                elif response.status_code == 404:
                    self.stdout.write(self.style.WARNING("⚠ 테스트 이미지가 없어 정확한 테스트 불가"))
                else:
                    self.stdout.write(self.style.ERROR("✗ 예상과 다른 결과"))
                    
            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f"요청 실패: {e}"))
        
        self.stdout.write(f"\n{self.style.SUCCESS('테스트 완료!')}")
        self.stdout.write("\n참고사항:")
        self.stdout.write("- 실제 이미지 파일이 없으면 404 오류가 발생할 수 있습니다")
        self.stdout.write("- 개발 서버가 실행 중이어야 테스트가 가능합니다")
        self.stdout.write("- 로그는 Django 로그 설정에 따라 콘솔이나 파일에 기록됩니다") 
