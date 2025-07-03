from django.core.management.base import BaseCommand
from django.core.cache import cache


class Command(BaseCommand):
    help = '사이트 설정 캐시를 클리어합니다'

    def handle(self, *args, **options):
        # 사이트 설정 캐시 클리어
        cache.delete('site_settings_singleton')
        
        self.stdout.write(
            self.style.SUCCESS('✅ 사이트 설정 캐시가 클리어되었습니다.')
        ) 