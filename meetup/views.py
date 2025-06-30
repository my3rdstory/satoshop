from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from stores.models import Store

def meetup_list(request, store_id):
    """밋업 목록 (공개/관리자 뷰)"""
    try:
        store = Store.objects.get(store_id=store_id, deleted_at__isnull=True)
    except Store.DoesNotExist:
        raise Http404("스토어를 찾을 수 없습니다.")
    
    # 스토어 소유자인지 확인하여 관리자/공개 뷰 결정
    is_public_view = request.user != store.owner
    
    # 임시로 빈 목록 반환 (추후 모델 생성 후 수정)
    meetups = []
    categories = []
    
    context = {
        'store': store,
        'meetups': meetups,
        'categories': categories,
        'is_public_view': is_public_view,
    }
    
    return render(request, 'meetup/meetup_list.html', context)

@login_required
def add_meetup(request, store_id):
    """밋업 추가"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    if request.method == 'POST':
        # 추후 구현
        messages.success(request, '밋업이 성공적으로 추가되었습니다.')
        return redirect('meetup:meetup_list', store_id=store_id)
    
    context = {
        'store': store,
    }
    
    return render(request, 'meetup/meetup_add.html', context)

def meetup_detail(request, store_id, meetup_id):
    """밋업 상세"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    
    # 임시로 빈 컨텍스트 반환 (추후 모델 생성 후 수정)
    context = {
        'store': store,
        'meetup_id': meetup_id,
    }
    
    return render(request, 'meetup/meetup_detail.html', context)

@login_required
def manage_meetup(request, store_id, meetup_id):
    """밋업 관리"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    # 임시로 빈 컨텍스트 반환 (추후 모델 생성 후 수정)
    context = {
        'store': store,
        'meetup_id': meetup_id,
    }
    
    return render(request, 'meetup/meetup_manage.html', context)

@login_required
def category_manage(request, store_id):
    """카테고리 관리"""
    store = get_object_or_404(Store, store_id=store_id, owner=request.user, deleted_at__isnull=True)
    
    # 임시로 빈 컨텍스트 반환 (추후 모델 생성 후 수정)
    context = {
        'store': store,
        'categories': [],
    }
    
    return render(request, 'meetup/category_manage.html', context)

def get_categories(request, store_id):
    """카테고리 목록 API"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    
    # 임시로 빈 목록 반환 (추후 모델 생성 후 수정)
    categories = []
    
    return JsonResponse({
        'categories': categories
    })
