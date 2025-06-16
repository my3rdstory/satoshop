from django.core.management.base import BaseCommand
from django.contrib.staticfiles.finders import find
from django.conf import settings
import hashlib
import os
import glob

class Command(BaseCommand):
    help = '정적 파일들의 해시 정보를 표시합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['css', 'js', 'all'],
            default='all',
            help='표시할 파일 타입 (css, js, all)',
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='상세 정보 표시 (파일 크기, 수정 시간 포함)',
        )

    def get_file_hash(self, file_path):
        """파일의 MD5 해시를 계산합니다."""
        absolute_path = find(file_path)
        if not absolute_path or not os.path.exists(absolute_path):
            return None
        
        try:
            with open(absolute_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()[:8]
        except (IOError, OSError):
            return None

    def get_file_info(self, file_path):
        """파일의 상세 정보를 가져옵니다."""
        absolute_path = find(file_path)
        if not absolute_path or not os.path.exists(absolute_path):
            return None
        
        try:
            stat = os.stat(absolute_path)
            return {
                'size': stat.st_size,
                'mtime': stat.st_mtime,
            }
        except (IOError, OSError):
            return None

    def format_size(self, size_bytes):
        """바이트를 읽기 쉬운 형태로 변환합니다."""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f}KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f}MB"

    def handle(self, *args, **options):
        static_dirs = getattr(settings, 'STATICFILES_DIRS', [])
        if not static_dirs:
            self.stdout.write(
                self.style.ERROR('❌ STATICFILES_DIRS가 설정되지 않았습니다.')
            )
            return

        file_patterns = []
        if options['type'] in ['css', 'all']:
            file_patterns.extend(['css/*.css'])
        if options['type'] in ['js', 'all']:
            file_patterns.extend(['js/*.js'])

        self.stdout.write(
            self.style.SUCCESS(f'📊 정적 파일 해시 정보 ({options["type"]} 파일)')
        )
        self.stdout.write('=' * 80)

        total_files = 0
        for static_dir in static_dirs:
            for pattern in file_patterns:
                full_pattern = os.path.join(static_dir, pattern)
                files = glob.glob(full_pattern)
                
                for file_path in sorted(files):
                    relative_path = os.path.relpath(file_path, static_dir)
                    file_hash = self.get_file_hash(relative_path)
                    
                    if file_hash:
                        total_files += 1
                        output = f"📄 {relative_path:<40} | 🔑 {file_hash}"
                        
                        if options['detailed']:
                            file_info = self.get_file_info(relative_path)
                            if file_info:
                                size_str = self.format_size(file_info['size'])
                                output += f" | 📦 {size_str:<8}"
                        
                        self.stdout.write(output)
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"⚠️ {relative_path} - 해시 생성 실패")
                        )

        self.stdout.write('=' * 80)
        self.stdout.write(
            self.style.SUCCESS(f'✅ 총 {total_files}개의 파일 처리 완료')
        )

        # ManifestStaticFilesStorage 사용 여부 확인
        if hasattr(settings, 'STATICFILES_STORAGE') and 'Manifest' in settings.STATICFILES_STORAGE:
            self.stdout.write(
                self.style.SUCCESS('🔄 ManifestStaticFilesStorage가 활성화되어 있습니다.')
            )
            manifest_path = os.path.join(settings.STATIC_ROOT, 'staticfiles.json')
            if os.path.exists(manifest_path):
                self.stdout.write(
                    self.style.SUCCESS(f'📋 매니페스트 파일: {manifest_path}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('⚠️ 매니페스트 파일이 없습니다. collectstatic을 실행하세요.')
                ) 