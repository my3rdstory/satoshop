from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
import os
import glob

class Command(BaseCommand):
    help = '정적 파일 해시 캐시를 지웁니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--pattern',
            type=str,
            help='특정 패턴의 캐시만 지우기 (예: css/*, js/*)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='모든 정적 파일 캐시 지우기',
        )

    def handle(self, *args, **options):
        if options['all']:
            # 모든 static_hash_ 캐시 키 지우기
            cache_keys = cache.keys('static_hash_*')
            if cache_keys:
                cache.delete_many(cache_keys)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ {len(cache_keys)}개의 정적 파일 캐시를 지웠습니다.')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️ 지울 캐시가 없습니다.')
                )
        elif options['pattern']:
            pattern = options['pattern']
            cache_pattern = f"static_hash_{pattern}"
            cache_keys = cache.keys(cache_pattern)
            if cache_keys:
                cache.delete_many(cache_keys)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ 패턴 "{pattern}"에 해당하는 {len(cache_keys)}개의 캐시를 지웠습니다.')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️ 패턴 "{pattern}"에 해당하는 캐시가 없습니다.')
                )
        else:
            self.stdout.write(
                self.style.ERROR('❌ --all 또는 --pattern 옵션을 사용해주세요.')
            )
            return

        self.stdout.write(
            self.style.SUCCESS('🔄 다음 요청시 새로운 해시가 생성됩니다.')
        ) 