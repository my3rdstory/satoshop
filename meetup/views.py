from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.db import transaction
from stores.models import Store
from .models import Meetup, MeetupImage, MeetupOption, MeetupChoice
from .forms import MeetupForm
import json

def meetup_list(request, store_id):
    """밋업 목록 (공개/관리자 뷰)"""
    try:
        store = Store.objects.get(store_id=store_id, deleted_at__isnull=True)
    except Store.DoesNotExist:
        raise Http404("스토어를 찾을 수 없습니다.")
    
    # 스토어 소유자인지 확인하여 관리자/공개 뷰 결정
    is_public_view = request.user != store.owner
    
    # 밋업 목록 조회
    meetups_queryset = Meetup.objects.filter(
        store=store, 
        deleted_at__isnull=True
    ).prefetch_related('images')
    
    # 공개 뷰에서는 활성화된 밋업만 표시
    if is_public_view:
        meetups_queryset = meetups_queryset.filter(
            is_active=True,
            is_temporarily_closed=False
        )
    
    meetups = meetups_queryset.order_by('-created_at')
    
    context = {
        'store': store,
        'meetups': meetups,
        'is_public_view': is_public_view,
    }
    
    return render(request, 'meetup/meetup_list.html', context)

@login_required
def add_meetup(request, store_id):
    """밋업 추가"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    if request.method == 'POST':
        form = MeetupForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 밋업 생성
                    meetup = form.save(commit=False)
                    meetup.store = store
                    meetup.save()
                    
                    # 이미지 업로드 처리
                    images = request.FILES.getlist('images')
                    if images:
                        # 밋업당 1장만 허용
                        image_file = images[0]
                        try:
                            from storage.utils import upload_meetup_image
                            result = upload_meetup_image(image_file, meetup, request.user)
                            
                            if result['success']:
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.info(f"밋업 이미지 업로드 성공: {image_file.name}")
                            else:
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.warning(f"밋업 이미지 업로드 실패: {image_file.name}, 오류: {result['error']}")
                                messages.warning(request, f'이미지 업로드 실패: {result["error"]}')
                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"밋업 이미지 처리 오류: {e}", exc_info=True)
                            messages.warning(request, '이미지 업로드 중 오류가 발생했습니다.')
                    
                    # 옵션 처리 (JavaScript에서 전송된 데이터)
                    options_data = request.POST.get('options_json')
                    if options_data:
                        try:
                            options = json.loads(options_data)
                            for option_data in options:
                                option = MeetupOption.objects.create(
                                    meetup=meetup,
                                    name=option_data.get('name', ''),
                                    is_required=option_data.get('is_required', False),
                                    order=option_data.get('order', 0)
                                )
                                
                                # 선택지 생성
                                for choice_data in option_data.get('choices', []):
                                    MeetupChoice.objects.create(
                                        option=option,
                                        name=choice_data.get('name', ''),
                                        additional_price=choice_data.get('additional_price', 0),
                                        order=choice_data.get('order', 0)
                                    )
                        except json.JSONDecodeError:
                            pass  # 옵션 데이터 파싱 오류는 무시하고 계속 진행
                    
                    messages.success(request, f'"{meetup.name}" 밋업이 성공적으로 추가되었습니다.')
                    return redirect('meetup:meetup_list', store_id=store_id)
                    
            except Exception as e:
                messages.error(request, '밋업 추가 중 오류가 발생했습니다. 다시 시도해주세요.')
                print(f"Error creating meetup: {e}")  # 디버그용
    else:
        form = MeetupForm()
    
    context = {
        'store': store,
        'form': form,
    }
    
    return render(request, 'meetup/meetup_add.html', context)

def meetup_detail(request, store_id, meetup_id):
    """밋업 상세"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup, 
        id=meetup_id, 
        store=store, 
        deleted_at__isnull=True
    )
    
    # 공개 뷰에서는 비활성화된 밋업 접근 차단
    if request.user != store.owner:
        if not meetup.is_active or meetup.is_temporarily_closed:
            raise Http404("밋업을 찾을 수 없습니다.")
    
    # 밋업 옵션 조회
    meetup_options = meetup.options.prefetch_related('choices').order_by('order')
    
    context = {
        'store': store,
        'meetup': meetup,
        'meetup_options': meetup_options,
        'meetup_id': meetup_id,
    }
    
    return render(request, 'meetup/meetup_detail.html', context)

@login_required
def edit_meetup_unified(request, store_id, meetup_id):
    """밋업 통합수정"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup, 
        id=meetup_id, 
        store=store, 
        deleted_at__isnull=True
    )
    
    if request.method == 'POST':
        form = MeetupForm(data=request.POST, files=request.FILES, instance=meetup)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 밋업 수정
                    meetup = form.save()
                    
                    # 새 이미지 업로드 처리
                    images = request.FILES.getlist('images')
                    if images:
                        # 기존 이미지가 있으면 삭제 (밋업당 1장만 허용)
                        existing_images = meetup.images.all()
                        if existing_images.exists():
                            for existing_image in existing_images:
                                # S3에서 파일 삭제
                                try:
                                    from storage.utils import delete_file_from_s3
                                    delete_file_from_s3(existing_image.file_path)
                                except Exception as e:
                                    import logging
                                    logger = logging.getLogger(__name__)
                                    logger.warning(f"S3 파일 삭제 실패: {e}")
                                # DB에서 삭제
                                existing_image.delete()
                        
                        # 새 이미지 업로드 (첫 번째 이미지만)
                        image_file = images[0]
                        try:
                            from storage.utils import upload_meetup_image
                            result = upload_meetup_image(image_file, meetup, request.user)
                            
                            if result['success']:
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.info(f"밋업 이미지 업로드 성공: {image_file.name}")
                            else:
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.warning(f"밋업 이미지 업로드 실패: {image_file.name}, 오류: {result['error']}")
                                messages.warning(request, f'이미지 업로드 실패: {result["error"]}')
                        except Exception as e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"밋업 이미지 처리 오류: {e}", exc_info=True)
                            messages.warning(request, '이미지 업로드 중 오류가 발생했습니다.')
                    
                    # 옵션 처리 (기존 옵션 삭제 후 재생성)
                    options_data = request.POST.get('options_json')
                    if options_data:
                        try:
                            # 기존 옵션 삭제
                            meetup.options.all().delete()
                            
                            options = json.loads(options_data)
                            for option_data in options:
                                option = MeetupOption.objects.create(
                                    meetup=meetup,
                                    name=option_data.get('name', ''),
                                    is_required=option_data.get('is_required', False),
                                    order=option_data.get('order', 0)
                                )
                                
                                # 선택지 생성
                                for choice_data in option_data.get('choices', []):
                                    MeetupChoice.objects.create(
                                        option=option,
                                        name=choice_data.get('name', ''),
                                        additional_price=choice_data.get('additional_price', 0),
                                        order=choice_data.get('order', 0)
                                    )
                        except json.JSONDecodeError:
                            pass  # 옵션 데이터 파싱 오류는 무시하고 계속 진행
                    
                    messages.success(request, f'"{meetup.name}" 밋업이 성공적으로 수정되었습니다.')
                    return redirect('meetup:meetup_list', store_id=store_id)
                    
            except Exception as e:
                messages.error(request, '밋업 수정 중 오류가 발생했습니다. 다시 시도해주세요.')
                print(f"Error updating meetup: {e}")  # 디버그용
    else:
        form = MeetupForm(instance=meetup)
    
    # 기존 옵션 데이터를 JSON으로 변환
    existing_options = []
    for option in meetup.options.all():
        option_data = {
            'name': option.name,
            'is_required': option.is_required,
            'order': option.order,
            'choices': []
        }
        for choice in option.choices.all():
            choice_data = {
                'name': choice.name,
                'additional_price': choice.additional_price,
                'order': choice.order
            }
            option_data['choices'].append(choice_data)
        existing_options.append(option_data)
    
    context = {
        'store': store,
        'meetup': meetup,
        'form': form,
        'existing_options': json.dumps(existing_options),
        'is_edit': True,
    }
    
    return render(request, 'meetup/meetup_edit.html', context)

@login_required
def manage_meetup(request, store_id, meetup_id):
    """밋업 관리"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    meetup = get_object_or_404(
        Meetup, 
        id=meetup_id, 
        store=store, 
        deleted_at__isnull=True
    )
    
    context = {
        'store': store,
        'meetup': meetup,
        'meetup_id': meetup_id,
    }
    
    return render(request, 'meetup/meetup_manage.html', context)
