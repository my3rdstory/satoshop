"""
만료된 임시 업로드 파일들을 정리하는 management command
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from commons.storage.models import TemporaryUpload


class Command(BaseCommand):
    help = '만료된 임시 업로드 파일들을 정리합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제로 삭제하지 않고 삭제될 파일들만 출력',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='몇 일 전 파일까지 삭제할지 설정 (기본값: 1일)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        days = options['days']
        
        # 기준 시간 계산 (현재 시간 - 지정된 일수)
        cutoff_time = timezone.now() - timezone.timedelta(days=days)
        
        # 만료된 임시 파일들 조회
        expired_files = TemporaryUpload.objects.filter(
            expires_at__lt=cutoff_time
        )
        
        total_count = expired_files.count()
        
        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS('정리할 만료된 임시 파일이 없습니다.')
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'[DRY RUN] 삭제될 파일들 ({total_count}개):')
            )
            for temp_file in expired_files:
                self.stdout.write(f'  - {temp_file.original_name} ({temp_file.file_path})')
        else:
            self.stdout.write(f'만료된 임시 파일 {total_count}개를 정리합니다...')
            
            # S3에서 파일 삭제 및 DB에서 제거
            success_count = 0
            error_count = 0
            
            for temp_file in expired_files:
                try:
                    from commons.storage.utils import delete_file_from_s3
                    
                    # S3에서 파일 삭제
                    result = delete_file_from_s3(temp_file.file_path)
                    
                    if result['success']:
                        # DB에서 제거
                        temp_file.delete()
                        success_count += 1
                        self.stdout.write(f'  ✓ {temp_file.original_name}')
                    else:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ {temp_file.original_name}: {result["error"]}')
                        )
                
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ {temp_file.original_name}: {str(e)}')
                    )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'정리 완료: 성공 {success_count}개, 실패 {error_count}개'
                )
            ) 