from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.generic import ListView
from django.http import JsonResponse
from .models import HallOfFame
from storage.utils import upload_file_to_s3
from django.core.files.base import ContentFile
import io
import logging

from .cache_utils import (
    get_hall_of_fame_filters_cache,
    get_hall_of_fame_list_cache,
    set_hall_of_fame_filters_cache,
    set_hall_of_fame_list_cache,
)

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def has_hall_of_fame_permission(user):
    """Hall of Fame 등록 권한 확인"""
    from .models import HallOfFamePermission
    if user.is_staff or user.is_superuser:
        return True
    try:
        permission = HallOfFamePermission.objects.get(user=user, can_upload=True)
        return True
    except HallOfFamePermission.DoesNotExist:
        return False


def _normalize_year(raw_value):
    if raw_value in (None, ""):
        return None
    try:
        year = int(str(raw_value).strip())
    except (TypeError, ValueError):
        return None
    return year if year > 0 else None


def _normalize_month(raw_value):
    if raw_value in (None, ""):
        return None
    try:
        month = int(str(raw_value).strip())
    except (TypeError, ValueError):
        return None
    return month if 1 <= month <= 12 else None


def _build_hall_of_fame_list_suffix(year, month):
    year_part = f"year:{year}" if year is not None else "year:all"
    month_part = f"month:{month}" if month is not None else "month:all"
    return f"{year_part}|{month_part}"


def _get_cached_hall_of_fame_list(year=None, month=None):
    cache_suffix = _build_hall_of_fame_list_suffix(year, month)
    cached = get_hall_of_fame_list_cache(cache_suffix)
    if cached is not None:
        return cached

    queryset = HallOfFame.objects.filter(is_active=True)
    if year is not None:
        queryset = queryset.filter(year=year)
    if month is not None:
        queryset = queryset.filter(month=month)

    queryset = queryset.select_related('created_by').order_by('-created_at')
    results = list(queryset)
    set_hall_of_fame_list_cache(cache_suffix, results)
    return results


def _get_cached_hall_of_fame_years():
    cache_suffix = "years"
    cached = get_hall_of_fame_filters_cache(cache_suffix)
    if cached is not None:
        return cached

    years = list(
        HallOfFame.objects.filter(is_active=True)
        .values_list('year', flat=True)
        .distinct()
        .order_by('year')
    )
    set_hall_of_fame_filters_cache(cache_suffix, years)
    return years


def _get_cached_hall_of_fame_months(year=None):
    cache_suffix = f"months:{year}" if year is not None else "months:all"
    cached = get_hall_of_fame_filters_cache(cache_suffix)
    if cached is not None:
        return cached

    queryset = HallOfFame.objects.filter(is_active=True)
    if year is not None:
        queryset = queryset.filter(year=year)

    months = list(
        queryset.values_list('month', flat=True)
        .distinct()
        .order_by('month')
    )
    set_hall_of_fame_filters_cache(cache_suffix, months)
    return months


class HallOfFameListView(ListView):
    """Hall of Fame 목록 뷰"""
    model = HallOfFame
    template_name = 'boards/hall-of-fame/list.html'
    context_object_name = 'hall_of_fame_list'
    paginate_by = 20
    
    def get_queryset(self):
        year = _normalize_year(self.request.GET.get('year'))
        month = _normalize_month(self.request.GET.get('month'))
        return _get_cached_hall_of_fame_list(year, month)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 등록된 년도와 월 목록은 캐시에서 가져온다.
        selected_year_value = self.request.GET.get('year', '')
        normalized_year = _normalize_year(selected_year_value)
        context['years'] = _get_cached_hall_of_fame_years()
        context['months'] = _get_cached_hall_of_fame_months(normalized_year)
        
        # 현재 필터 값
        context['selected_year'] = self.request.GET.get('year', '')
        context['selected_month'] = self.request.GET.get('month', '')
        
        # 권한 체크
        context['can_create'] = has_hall_of_fame_permission(self.request.user) if self.request.user.is_authenticated else False
        context['can_delete'] = self.request.user.is_authenticated and (
            self.request.user.is_staff or self.request.user.is_superuser or 
            has_hall_of_fame_permission(self.request.user)
        )
        
        return context


@login_required
@user_passes_test(has_hall_of_fame_permission)
def hall_of_fame_create(request):
    """Hall of Fame 등록 뷰"""
    if request.method == 'POST':
        try:
            # 폼 데이터 추출
            year = request.POST.get('year')
            month = request.POST.get('month')
            image_file = request.FILES.get('image')
            
            # 유효성 검사
            if not year or not month or not image_file:
                messages.error(request, '필수 항목을 모두 입력해주세요.')
                return render(request, 'boards/hall-of-fame/create.html')
            
            # 이미지 처리 (1:1 비율로 썸네일 생성)
            process_result = process_hall_of_fame_image(image_file)
            if not process_result['success']:
                messages.error(request, f"이미지 처리 실패: {process_result.get('error', '알 수 없는 오류')}")
                return render(request, 'boards/hall-of-fame/create.html')
            
            # 원본 이미지 업로드
            original_upload_result = upload_file_to_s3(
                process_result['original_file'],
                prefix='hall_of_fame/originals'
            )
            
            if not original_upload_result['success']:
                messages.error(request, f"이미지 업로드 실패: {original_upload_result.get('error', '알 수 없는 오류')}")
                return render(request, 'boards/hall-of-fame/create.html')
            
            # 썸네일 업로드
            thumbnail_upload_result = upload_file_to_s3(
                process_result['thumbnail_file'],
                prefix='hall_of_fame/thumbnails'
            )
            
            if not thumbnail_upload_result['success']:
                messages.error(request, f"썸네일 업로드 실패: {thumbnail_upload_result.get('error', '알 수 없는 오류')}")
                return render(request, 'boards/hall-of-fame/create.html')
            
            # Hall of Fame 생성
            hall_of_fame = HallOfFame.objects.create(
                year=int(year),
                month=int(month),
                image_path=original_upload_result['file_path'],
                image_url=original_upload_result['file_url'],
                thumbnail_path=thumbnail_upload_result['file_path'],
                thumbnail_url=thumbnail_upload_result['file_url'],
                original_filename=image_file.name,
                file_size=original_upload_result['file_size'],
                width=process_result['original_size'][0],
                height=process_result['original_size'][1],
                created_by=request.user
            )
            
            messages.success(request, 'Hall of Fame이 성공적으로 등록되었습니다.')
            return redirect('boards:hall_of_fame_list')
            
        except Exception as e:
            logger.error(f"Hall of Fame 생성 오류: {str(e)}")
            messages.error(request, f'등록 중 오류가 발생했습니다: {str(e)}')
            return render(request, 'boards/hall-of-fame/create.html')
    
    return render(request, 'boards/hall-of-fame/create.html')


def process_hall_of_fame_image(image_file, thumbnail_size=400):
    """
    Hall of Fame 이미지를 처리합니다.
    - 원본은 1:1 비율로 크롭 후 1000x1000 리사이즈
    - 썸네일은 400x400 생성
    - WebP 포맷으로 변환
    """
    try:
        if not PIL_AVAILABLE:
            return {
                'success': False,
                'error': 'Pillow 패키지가 설치되지 않았습니다.'
            }
        
        logger.info(f"Hall of Fame 이미지 처리 시작: {image_file.name}")
        
        # 이미지 열기
        image = Image.open(image_file)
        original_size = image.size
        logger.info(f"원본 이미지 크기: {original_size}")
        
        # EXIF 정보에 따른 회전 보정
        image = ImageOps.exif_transpose(image)
        
        # RGB 모드로 변환
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGB')
        elif image.mode == 'RGBA':
            # 투명 배경을 흰색으로 변환
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        
        # 1:1 비율로 중앙 크롭
        width, height = image.size
        min_dimension = min(width, height)
        
        left = (width - min_dimension) // 2
        top = (height - min_dimension) // 2
        right = left + min_dimension
        bottom = top + min_dimension
        
        image_cropped = image.crop((left, top, right, bottom))
        logger.info(f"1:1 크롭 완료: {image_cropped.size}")
        
        # 원본 이미지 리사이즈 (1000x1000)
        original_resized = image_cropped.resize((1000, 1000), Image.Resampling.LANCZOS)
        
        # 썸네일 생성 (400x400)
        thumbnail = image_cropped.resize((thumbnail_size, thumbnail_size), Image.Resampling.LANCZOS)
        
        # 원본 WebP 변환
        original_output = io.BytesIO()
        original_resized.save(original_output, format='WEBP', quality=85, method=6)
        original_output.seek(0)
        
        # 썸네일 WebP 변환
        thumbnail_output = io.BytesIO()
        thumbnail.save(thumbnail_output, format='WEBP', quality=85, method=6)
        thumbnail_output.seek(0)
        
        # ContentFile 생성
        base_name = image_file.name.rsplit('.', 1)[0]
        original_file = ContentFile(original_output.getvalue(), name=f"{base_name}_original.webp")
        thumbnail_file = ContentFile(thumbnail_output.getvalue(), name=f"{base_name}_thumbnail.webp")
        
        return {
            'success': True,
            'original_file': original_file,
            'thumbnail_file': thumbnail_file,
            'original_size': (1000, 1000),
            'thumbnail_size': (thumbnail_size, thumbnail_size)
        }
        
    except Exception as e:
        error_msg = f"Hall of Fame 이미지 처리 실패: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        }


@login_required
def check_hall_of_fame(request):
    """Hall of Fame 연/월 충돌 여부와 기존 등록 수를 조회하는 API"""
    if not has_hall_of_fame_permission(request.user):
        return JsonResponse({'error': '권한이 없습니다.'}, status=403)
    
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if not year or not month:
        return JsonResponse({'exists': False, 'count': 0})

    from .models import HallOfFame
    queryset = HallOfFame.objects.filter(year=year, month=month)
    count = queryset.count()

    return JsonResponse({'exists': count > 0, 'count': count})


@login_required
@user_passes_test(has_hall_of_fame_permission)
def hall_of_fame_delete(request, pk):
    """Hall of Fame 삭제"""
    hall_of_fame = get_object_or_404(HallOfFame, pk=pk)
    
    # 권한 확인 (관리자이거나 등록한 본인만 삭제 가능)
    if not (request.user.is_staff or request.user.is_superuser or hall_of_fame.created_by == request.user):
        messages.error(request, '삭제 권한이 없습니다.')
        return redirect('boards:hall_of_fame_list')
    
    # POST 요청일 때만 삭제 (확인창에서 확인 후)
    if request.method == 'POST':
        try:
            year = hall_of_fame.year
            month = hall_of_fame.month
            
            # 삭제 (모델의 delete 메서드가 S3 파일도 함께 삭제)
            hall_of_fame.delete()
            
            messages.success(request, f'{year}년 {month}월 Hall of Fame이 성공적으로 삭제되었습니다.')
            logger.info(f"Hall of Fame 삭제 완료: {year}년 {month}월 (사용자: {request.user.username})")
            
        except Exception as e:
            logger.error(f"Hall of Fame 삭제 오류 (ID: {pk}): {str(e)}")
            messages.error(request, f'삭제 중 오류가 발생했습니다: {str(e)}')
    
    return redirect('boards:hall_of_fame_list')


def hall_of_fame_list_api(request):
    """Hall of Fame 목록 API (비동기 필터링용)"""
    from django.template.loader import render_to_string
    
    try:
        year = _normalize_year(request.GET.get('year'))
        month = _normalize_month(request.GET.get('month'))
        hall_of_fame_list = _get_cached_hall_of_fame_list(year, month)
        
        # 권한 체크
        can_delete = request.user.is_authenticated and (
            request.user.is_staff or request.user.is_superuser or 
            has_hall_of_fame_permission(request.user)
        )
        
        # HTML 렌더링
        html = render_to_string('boards/hall-of-fame/grid_partial.html', {
            'hall_of_fame_list': hall_of_fame_list,
            'can_delete': can_delete,
            'user': request.user
        }, request=request)
        
        return JsonResponse({
            'success': True,
            'html': html,
            'count': len(hall_of_fame_list)
        })
        
    except Exception as e:
        logger.error(f"Hall of Fame 목록 API 오류: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


def hall_of_fame_months_api(request):
    """특정 년도의 월 목록 API"""
    try:
        year = _normalize_year(request.GET.get('year'))
        months_list = _get_cached_hall_of_fame_months(year)

        return JsonResponse({
            'success': True,
            'months': months_list
        })
        
    except Exception as e:
        logger.error(f"Hall of Fame 월 목록 API 오류: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
