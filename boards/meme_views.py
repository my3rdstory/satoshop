from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, F
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
import json
import logging

from .models import MemePost, MemeTag
from .meme_forms import MemePostForm
from .meme_utils import process_meme_image, create_meme_thumbnail, validate_meme_image
from storage.utils import upload_meme_image, delete_meme_images

logger = logging.getLogger(__name__)


class MemeListView(ListView):
    """밈 게시글 목록 뷰"""
    model = MemePost
    template_name = 'boards/meme/list.html'
    context_object_name = 'memes'
    paginate_by = 15  # 5개 x 3줄
    
    def get_queryset(self):
        queryset = MemePost.objects.filter(is_active=True).select_related('author').prefetch_related('tags')
        
        # 검색 기능
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(tags__name__icontains=search)
            ).distinct()
        
        # 태그 필터
        tag = self.request.GET.get('tag')
        if tag:
            queryset = queryset.filter(tags__name=tag)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['selected_tag'] = self.request.GET.get('tag', '')
        context['can_create'] = self.request.user.is_authenticated
        return context


class MemeDetailView(DetailView):
    """밈 게시글 상세 뷰"""
    model = MemePost
    template_name = 'boards/meme/detail.html'
    context_object_name = 'meme'
    
    def get_object(self):
        obj = get_object_or_404(MemePost, pk=self.kwargs['pk'], is_active=True)
        # 조회수 증가
        obj.increase_views()
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        meme = self.get_object()
        
        # 수정/삭제 권한 체크
        context['can_edit'] = (
            self.request.user.is_authenticated and (
                self.request.user == meme.author or 
                self.request.user.is_staff or 
                self.request.user.is_superuser
            )
        )
        context['can_create'] = self.request.user.is_authenticated
        return context


@login_required
def meme_create(request):
    """밈 게시글 작성"""
    if request.method == 'POST':
        form = MemePostForm(request.POST)
        
        if form.is_valid():
            # 이미지 파일 확인
            image_file = request.FILES.get('image')
            if not image_file:
                messages.error(request, '이미지를 선택해주세요.')
                return render(request, 'boards/meme/create.html', {'form': form})
            
            # 이미지 검증
            validation = validate_meme_image(image_file)
            if not validation['is_valid']:
                for error in validation['errors']:
                    messages.error(request, error)
                return render(request, 'boards/meme/create.html', {'form': form})
            
            # 이미지 처리
            process_result = process_meme_image(image_file)
            if not process_result['success']:
                messages.error(request, process_result['error'])
                return render(request, 'boards/meme/create.html', {'form': form})
            
            # 썸네일 생성
            thumbnail_result = create_meme_thumbnail(process_result['processed_file'])
            if not thumbnail_result['success']:
                messages.error(request, thumbnail_result['error'])
                return render(request, 'boards/meme/create.html', {'form': form})
            
            # S3 업로드
            upload_result = upload_meme_image(
                image_file,
                process_result['processed_file'],
                thumbnail_result['thumbnail_file'],
                request.user
            )
            
            if not upload_result['success']:
                messages.error(request, upload_result['error'])
                return render(request, 'boards/meme/create.html', {'form': form})
            
            # 게시글 저장
            meme = form.save(commit=False)
            meme.author = request.user
            meme.image_path = upload_result['original_path']
            meme.image_url = upload_result['original_url']
            meme.thumbnail_path = upload_result['thumbnail_path']
            meme.thumbnail_url = upload_result['thumbnail_url']
            meme.original_filename = upload_result['original_filename']
            meme.file_size = upload_result['file_size']
            meme.width = upload_result['width']
            meme.height = upload_result['height']
            
            form.save(commit=True)  # 태그 저장을 위해
            
            messages.success(request, '밈이 등록되었습니다.')
            return redirect('boards:meme_detail', pk=meme.pk)
    else:
        form = MemePostForm()
    
    return render(request, 'boards/meme/create.html', {
        'form': form,
        'can_create': True
    })


@login_required
def meme_edit(request, pk):
    """밈 게시글 수정"""
    meme = get_object_or_404(MemePost, pk=pk, is_active=True)
    
    # 권한 체크
    if not (request.user == meme.author or request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden("수정 권한이 없습니다.")
    
    if request.method == 'POST':
        form = MemePostForm(request.POST, instance=meme)
        
        if form.is_valid():
            # 새 이미지가 업로드된 경우
            image_file = request.FILES.get('image')
            if image_file:
                # 이미지 검증
                validation = validate_meme_image(image_file)
                if not validation['is_valid']:
                    for error in validation['errors']:
                        messages.error(request, error)
                    return render(request, 'boards/meme/edit.html', {'form': form, 'meme': meme})
                
                # 이미지 처리
                process_result = process_meme_image(image_file)
                if not process_result['success']:
                    messages.error(request, process_result['error'])
                    return render(request, 'boards/meme/edit.html', {'form': form, 'meme': meme})
                
                # 썸네일 생성
                thumbnail_result = create_meme_thumbnail(process_result['processed_file'])
                if not thumbnail_result['success']:
                    messages.error(request, thumbnail_result['error'])
                    return render(request, 'boards/meme/edit.html', {'form': form, 'meme': meme})
                
                # 기존 이미지 삭제
                old_original_path = meme.image_path
                old_thumbnail_path = meme.thumbnail_path
                
                # 새 이미지 업로드
                upload_result = upload_meme_image(
                    image_file,
                    process_result['processed_file'],
                    thumbnail_result['thumbnail_file'],
                    request.user
                )
                
                if not upload_result['success']:
                    messages.error(request, upload_result['error'])
                    return render(request, 'boards/meme/edit.html', {'form': form, 'meme': meme})
                
                # 게시글 업데이트
                meme.image_path = upload_result['original_path']
                meme.image_url = upload_result['original_url']
                meme.thumbnail_path = upload_result['thumbnail_path']
                meme.thumbnail_url = upload_result['thumbnail_url']
                meme.original_filename = upload_result['original_filename']
                meme.file_size = upload_result['file_size']
                meme.width = upload_result['width']
                meme.height = upload_result['height']
                
                # 기존 이미지 삭제
                delete_meme_images(old_original_path, old_thumbnail_path)
            
            form.save()
            messages.success(request, '밈이 수정되었습니다.')
            return redirect('boards:meme_detail', pk=meme.pk)
    else:
        form = MemePostForm(instance=meme)
    
    return render(request, 'boards/meme/edit.html', {
        'form': form,
        'meme': meme,
        'can_edit': True
    })


@login_required
def meme_delete(request, pk):
    """밈 게시글 삭제"""
    meme = get_object_or_404(MemePost, pk=pk, is_active=True)
    
    # 권한 체크
    if not (request.user == meme.author or request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden("삭제 권한이 없습니다.")
    
    if request.method == 'POST':
        # S3에서 이미지 삭제
        delete_result = delete_meme_images(meme.image_path, meme.thumbnail_path)
        
        if not delete_result['success']:
            messages.error(request, '이미지 삭제 중 오류가 발생했습니다.')
        
        # 게시글 비활성화
        meme.is_active = False
        meme.save()
        
        messages.success(request, '밈이 삭제되었습니다.')
        return redirect('boards:meme_list')
    
    return render(request, 'boards/meme/delete.html', {
        'meme': meme,
        'can_delete': True
    })


@require_POST
def meme_upload_image(request):
    """이미지 업로드 AJAX 처리"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': '로그인이 필요합니다.'}, status=403)
    
    image_file = request.FILES.get('image')
    if not image_file:
        return JsonResponse({'success': False, 'error': '이미지를 선택해주세요.'})
    
    # 이미지 검증
    validation = validate_meme_image(image_file)
    if not validation['is_valid']:
        return JsonResponse({'success': False, 'errors': validation['errors']})
    
    # 이미지 처리
    process_result = process_meme_image(image_file)
    if not process_result['success']:
        return JsonResponse({'success': False, 'error': process_result['error']})
    
    # 썸네일 생성
    thumbnail_result = create_meme_thumbnail(process_result['processed_file'])
    if not thumbnail_result['success']:
        return JsonResponse({'success': False, 'error': thumbnail_result['error']})
    
    # 임시 저장 (세션에 저장)
    request.session['temp_meme_image'] = {
        'original_filename': image_file.name,
        'processed_size': process_result['processed_size'],
        'is_gif': process_result['is_gif']
    }
    
    return JsonResponse({
        'success': True,
        'filename': image_file.name,
        'size': process_result['processed_size'],
        'is_gif': process_result['is_gif']
    })


def get_tag_cloud(request):
    """태그 클라우드 데이터 반환"""
    tags = MemeTag.objects.annotate(
        post_count=Count('memes', filter=Q(memes__is_active=True))
    ).filter(post_count__gt=0).order_by('-post_count', 'name')[:50]
    
    tag_data = [
        {
            'name': tag.name,
            'count': tag.post_count,
            'url': f"?tag={tag.name}"
        }
        for tag in tags
    ]
    
    return JsonResponse({'tags': tag_data})


@require_POST
def meme_increment_stat(request, pk):
    """밈 통계를 증가시킵니다."""
    meme = get_object_or_404(MemePost, pk=pk, is_active=True)
    
    # 요청에서 통계 타입 가져오기
    try:
        data = json.loads(request.body)
        stat_type = data.get('type')
    except:
        return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)
    
    # 통계 타입별로 증가
    if stat_type == 'list_copy':
        meme.list_copy_count = F('list_copy_count') + 1
    elif stat_type == 'list_view':
        meme.list_view_count = F('list_view_count') + 1
    elif stat_type == 'detail_copy':
        meme.detail_copy_count = F('detail_copy_count') + 1
    else:
        return JsonResponse({'error': '잘못된 통계 타입입니다.'}, status=400)
    
    meme.save(update_fields=[f'{stat_type}_count'])
    
    # 최신 값을 가져오기 위해 refresh
    meme.refresh_from_db()
    
    return JsonResponse({
        'success': True,
        'count': getattr(meme, f'{stat_type}_count')
    })