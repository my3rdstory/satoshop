from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.generic import ListView
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.db.models import Q
from .models import HallOfFame
from storage.utils import upload_file_to_s3, process_product_image
from django.core.files.base import ContentFile
import io
import logging

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def is_staff_or_superuser(user):
    """스태프 또는 슈퍼유저인지 확인"""
    return user.is_staff or user.is_superuser


class HallOfFameListView(ListView):
    """Hall of Fame 목록 뷰"""
    model = HallOfFame
    template_name = 'boards/hall-of-fame/list.html'
    context_object_name = 'hall_of_fame_list'
    paginate_by = 20
    
    def get_queryset(self):
        return HallOfFame.objects.filter(is_active=True).order_by('order', '-created_at')


@login_required
@user_passes_test(is_staff_or_superuser)
def hall_of_fame_create(request):
    """Hall of Fame 등록 뷰"""
    if request.method == 'POST':
        try:
            # 폼 데이터 추출
            user_id = request.POST.get('user_id')
            title = request.POST.get('title')
            description = request.POST.get('description', '')
            order = request.POST.get('order', 0)
            image_file = request.FILES.get('image')
            
            # 유효성 검사
            if not user_id or not title or not image_file:
                messages.error(request, '필수 항목을 모두 입력해주세요.')
                return render(request, 'boards/hall-of-fame/create.html')
            
            # 사용자 확인
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                messages.error(request, '선택한 사용자를 찾을 수 없습니다.')
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
                user=user,
                title=title,
                description=description,
                image_path=original_upload_result['file_path'],
                image_url=original_upload_result['file_url'],
                thumbnail_path=thumbnail_upload_result['file_path'],
                thumbnail_url=thumbnail_upload_result['file_url'],
                original_filename=image_file.name,
                file_size=original_upload_result['file_size'],
                width=process_result['original_size'][0],
                height=process_result['original_size'][1],
                order=int(order),
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
def search_users(request):
    """사용자 검색 API"""
    if not is_staff_or_superuser(request.user):
        return JsonResponse({'error': '권한이 없습니다.'}, status=403)
    
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    # 사용자 검색
    users = User.objects.filter(
        Q(username__icontains=query) | 
        Q(email__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query)
    )[:10]
    
    # JSON 응답 생성
    user_list = []
    for user in users:
        user_list.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.get_full_name() or ''
        })
    
    return JsonResponse({'users': user_list})