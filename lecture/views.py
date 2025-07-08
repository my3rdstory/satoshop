from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Avg
from django.utils import timezone
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.paginator import Paginator

from stores.models import Store
from .models import Lecture, Category, LectureEnrollment, LectureReview, LiveLecture, LiveLectureImage, LiveLectureOrder
from .forms import LiveLectureForm
import json
import logging

logger = logging.getLogger(__name__)


class LectureListView(ListView):
    """강의 목록"""
    model = Lecture
    template_name = 'lecture/list.html'
    context_object_name = 'lectures'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Lecture.objects.filter(status='published').select_related('category', 'instructor')
        
        # 카테고리 필터
        category_id = self.kwargs.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            
        # 검색
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search) |
                Q(instructor__first_name__icontains=search) |
                Q(instructor__last_name__icontains=search)
            )
        
        # 정렬
        sort = self.request.GET.get('sort', '-created_at')
        if sort in ['created_at', '-created_at', 'price', '-price', 'start_date', '-start_date']:
            queryset = queryset.order_by(sort)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['current_category'] = self.kwargs.get('category_id')
        context['search'] = self.request.GET.get('search', '')
        context['sort'] = self.request.GET.get('sort', '-created_at')
        return context


class LectureDetailView(DetailView):
    """강의 상세보기"""
    model = Lecture
    template_name = 'lecture/detail.html'
    context_object_name = 'lecture'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lecture = self.object
        
        # 리뷰
        reviews = lecture.reviews.all().select_related('student')
        context['reviews'] = reviews
        context['average_rating'] = reviews.aggregate(avg=Avg('rating'))['avg']
        
        # 사용자 수강 여부
        if self.request.user.is_authenticated:
            context['is_enrolled'] = LectureEnrollment.objects.filter(
                lecture=lecture, 
                student=self.request.user,
                status='active'
            ).exists()
            
            # 사용자 리뷰 여부
            context['user_review'] = LectureReview.objects.filter(
                lecture=lecture,
                student=self.request.user
            ).first()
        
        return context


@login_required
def enroll_lecture(request, pk):
    """강의 수강신청"""
    lecture = get_object_or_404(Lecture, pk=pk, status='published')
    
    # 이미 수강중인지 확인
    enrollment = LectureEnrollment.objects.filter(
        lecture=lecture,
        student=request.user
    ).first()
    
    if enrollment:
        if enrollment.status == 'active':
            messages.warning(request, '이미 수강 중인 강의입니다.')
        elif enrollment.status == 'cancelled':
            # 취소된 수강을 다시 활성화
            enrollment.status = 'active'
            enrollment.enrolled_at = timezone.now()
            enrollment.save()
            messages.success(request, '강의 수강신청이 완료되었습니다.')
        else:
            messages.info(request, '이미 수강완료한 강의입니다.')
    else:
        # 수강 인원 확인
        if lecture.is_full:
            messages.error(request, '수강 인원이 마감되었습니다.')
        else:
            # 새 수강신청
            LectureEnrollment.objects.create(
                lecture=lecture,
                student=request.user
            )
            messages.success(request, '강의 수강신청이 완료되었습니다.')
    
    return redirect('lecture:detail', pk=pk)


class MyLecturesView(LoginRequiredMixin, ListView):
    """내 강의 목록"""
    template_name = 'lecture/my_lectures.html'
    context_object_name = 'enrollments'
    paginate_by = 10
    
    def get_queryset(self):
        return LectureEnrollment.objects.filter(
            student=self.request.user
        ).select_related('lecture', 'lecture__category', 'lecture__instructor').order_by('-enrolled_at')


def check_admin_access(request, store):
    """수퍼어드민 특별 접근 확인 및 메시지 표시"""
    admin_access = request.GET.get('admin_access', '').lower() == 'true'
    is_superuser = request.user.is_superuser
    is_owner = store.owner == request.user
    
    # 스토어 소유자이거나 수퍼어드민이 admin_access 파라미터를 사용한 경우 접근 허용
    if is_owner or (is_superuser and admin_access):
        # 수퍼어드민이 다른 스토어에 접근하는 경우 알림 메시지 표시
        if is_superuser and admin_access and not is_owner:
            messages.info(request, f'관리자 권한으로 "{store.store_name}" 스토어에 접근 중입니다.')
        return True
    return False

def get_store_with_admin_check(request, store_id, require_auth=True):
    """스토어 조회 및 관리자 권한 확인"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    
    if require_auth and request.user.is_authenticated:
        if not check_admin_access(request, store):
            is_superuser = request.user.is_superuser
            if is_superuser:
                # 수퍼어드민인 경우 admin_access 파라미터 사용법 안내
                messages.error(request, 
                    '스토어 소유자만 접근할 수 있습니다. '
                    '관리자 권한으로 접근하려면 URL에 "?admin_access=true" 파라미터를 추가하세요.')
            else:
                messages.error(request, '스토어 소유자만 접근할 수 있습니다.')
            return None
    
    return store

def live_lecture_list(request, store_id):
    """라이브 강의 목록 (공개/관리자 뷰)"""
    try:
        store = Store.objects.get(store_id=store_id, deleted_at__isnull=True)
    except Store.DoesNotExist:
        raise Http404("스토어를 찾을 수 없습니다.")
    
    # 스토어 소유자인지 확인하여 관리자/공개 뷰 결정
    is_public_view = not (request.user.is_authenticated and check_admin_access(request, store))
    
    # 라이브 강의 목록 조회
    live_lectures_queryset = LiveLecture.objects.filter(
        store=store, 
        deleted_at__isnull=True
    ).prefetch_related('images')
    
    # 공개 뷰에서는 활성화된 라이브 강의만 표시
    if is_public_view:
        live_lectures_queryset = live_lectures_queryset.filter(
            is_active=True,
            is_temporarily_closed=False
        )
    
    live_lectures = live_lectures_queryset.order_by('-created_at')
    
    context = {
        'store': store,
        'live_lectures': live_lectures,
        'is_public_view': is_public_view,
    }
    
    return render(request, 'lecture/lecture_live_list.html', context)

def live_lecture_grid(request, store_id):
    """라이브 강의 그리드 뷰"""
    try:
        store = Store.objects.get(store_id=store_id, is_active=True, deleted_at__isnull=True)
    except Store.DoesNotExist:
        context = {
            'store_id': store_id,
            'error_type': 'store_not_found'
        }
        return render(request, 'lecture/store_not_found.html', context, status=404)
    
    live_lectures = LiveLecture.objects.filter(
        store=store, 
        is_active=True, 
        is_temporarily_closed=False,
        deleted_at__isnull=True
    ).prefetch_related('images').order_by('-created_at')
    
    context = {
        'store': store,
        'live_lectures': live_lectures,
        'is_public_view': True,
    }
    
    return render(request, 'lecture/lecture_live_grid.html', context)

@login_required
def add_live_lecture(request, store_id):
    """라이브 강의 추가"""
    store = get_store_with_admin_check(request, store_id)
    if not store:
        return redirect('myshop:home')
    
    if request.method == 'POST':
        form = LiveLectureForm(data=request.POST, files=request.FILES)
        logger.info(f"LiveLecture 폼 제출 - 사용자: {request.user}, 데이터: {request.POST}")
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 라이브 강의 생성
                    live_lecture = form.save(commit=False)
                    live_lecture.store = store
                    live_lecture.save()
                    
                    # 이미지 업로드 처리
                    images = request.FILES.getlist('images')
                    if images:
                        # 라이브 강의당 1장만 허용
                        image_file = images[0]
                        try:
                            from storage.utils import upload_live_lecture_image
                            result = upload_live_lecture_image(image_file, live_lecture, request.user)
                            
                            if result['success']:
                                logger.info(f"라이브 강의 이미지 업로드 성공: {image_file.name}")
                            else:
                                logger.warning(f"라이브 강의 이미지 업로드 실패: {image_file.name}, 오류: {result['error']}")
                                messages.warning(request, f'이미지 업로드 실패: {result["error"]}')
                        except Exception as e:
                            logger.error(f"라이브 강의 이미지 처리 오류: {e}", exc_info=True)
                            messages.warning(request, '이미지 업로드 중 오류가 발생했습니다.')
                    
                    messages.success(request, f'"{live_lecture.name}" 라이브 강의가 성공적으로 추가되었습니다.')
                    return redirect('lecture:live_lecture_list', store_id=store_id)
                    
            except Exception as e:
                messages.error(request, '라이브 강의 추가 중 오류가 발생했습니다. 다시 시도해주세요.')
                logger.error(f"Error creating live lecture: {e}", exc_info=True)
        else:
            logger.error(f"LiveLecture 폼 검증 실패 - 에러: {form.errors}")
            messages.error(request, '폼 검증에 실패했습니다. 입력 내용을 확인해주세요.')
    else:
        form = LiveLectureForm()
    
    context = {
        'store': store,
        'form': form,
    }
    
    return render(request, 'lecture/lecture_live_add.html', context)

def live_lecture_detail(request, store_id, live_lecture_id):
    """라이브 강의 상세"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    live_lecture = get_object_or_404(
        LiveLecture, 
        id=live_lecture_id, 
        store=store, 
        deleted_at__isnull=True
    )
    
    # 스토어 소유자인지 확인
    is_owner = request.user.is_authenticated and check_admin_access(request, store)
    
    # 비활성화된 라이브 강의는 소유자만 볼 수 있음
    if not live_lecture.is_active and not is_owner:
        raise Http404("라이브 강의를 찾을 수 없습니다.")
    
    # 일시중단된 라이브 강의는 소유자만 볼 수 있음
    if live_lecture.is_temporarily_closed and not is_owner:
        raise Http404("라이브 강의를 찾을 수 없습니다.")
    
    # 사용자의 참가 주문 확인
    user_order = None
    if request.user.is_authenticated:
        user_order = LiveLectureOrder.objects.filter(
            live_lecture=live_lecture,
            user=request.user
        ).first()
    
    context = {
        'store': store,
        'live_lecture': live_lecture,
        'user_order': user_order,
        'is_owner': is_owner,
    }
    
    return render(request, 'lecture/lecture_live_detail.html', context)

@login_required
def edit_live_lecture(request, store_id, live_lecture_id):
    """라이브 강의 수정"""
    store = get_store_with_admin_check(request, store_id)
    if not store:
        return redirect('myshop:home')
    
    live_lecture = get_object_or_404(
        LiveLecture, 
        id=live_lecture_id, 
        store=store, 
        deleted_at__isnull=True
    )
    
    if request.method == 'POST':
        form = LiveLectureForm(data=request.POST, files=request.FILES, instance=live_lecture)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 라이브 강의 수정
                    live_lecture = form.save()
                    
                    # 이미지 업로드 처리
                    images = request.FILES.getlist('images')
                    if images:
                        # 기존 이미지 삭제
                        live_lecture.images.all().delete()
                        
                        # 새 이미지 업로드 (1장만 허용)
                        image_file = images[0]
                        try:
                            from storage.utils import upload_live_lecture_image
                            result = upload_live_lecture_image(image_file, live_lecture, request.user)
                            
                            if result['success']:
                                logger.info(f"라이브 강의 이미지 업로드 성공: {image_file.name}")
                            else:
                                logger.warning(f"라이브 강의 이미지 업로드 실패: {image_file.name}, 오류: {result['error']}")
                                messages.warning(request, f'이미지 업로드 실패: {result["error"]}')
                        except Exception as e:
                            logger.error(f"라이브 강의 이미지 처리 오류: {e}", exc_info=True)
                            messages.warning(request, '이미지 업로드 중 오류가 발생했습니다.')
                    
                    messages.success(request, f'"{live_lecture.name}" 라이브 강의가 성공적으로 수정되었습니다.')
                    return redirect('lecture:live_lecture_detail', store_id=store_id, live_lecture_id=live_lecture_id)
                    
            except Exception as e:
                messages.error(request, '라이브 강의 수정 중 오류가 발생했습니다. 다시 시도해주세요.')
                logger.error(f"Error updating live lecture: {e}", exc_info=True)
    else:
        form = LiveLectureForm(instance=live_lecture)
    
    context = {
        'store': store,
        'live_lecture': live_lecture,
        'form': form,
    }
    
    return render(request, 'lecture/lecture_live_edit.html', context)

@login_required
def live_lecture_status(request, store_id):
    """라이브 강의 신청현황"""
    store = get_store_with_admin_check(request, store_id)
    if not store:
        return redirect('myshop:home')
    
    live_lectures = LiveLecture.objects.filter(
        store=store,
        deleted_at__isnull=True
    ).prefetch_related('orders').order_by('-created_at')
    
    context = {
        'store': store,
        'live_lectures': live_lectures,
    }
    
    return render(request, 'lecture/lecture_live_status.html', context)

@login_required
def live_lecture_status_detail(request, store_id, live_lecture_id):
    """라이브 강의 신청현황 상세"""
    store = get_store_with_admin_check(request, store_id)
    if not store:
        return redirect('myshop:home')
    
    live_lecture = get_object_or_404(
        LiveLecture, 
        id=live_lecture_id, 
        store=store, 
        deleted_at__isnull=True
    )
    
    # 주문 목록 조회
    orders = LiveLectureOrder.objects.filter(
        live_lecture=live_lecture
    ).select_related('user').order_by('-created_at')
    
    # 페이지네이션
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'store': store,
        'live_lecture': live_lecture,
        'orders': page_obj,
    }
    
    return render(request, 'lecture/lecture_live_status_detail.html', context)

@login_required
def live_lecture_checkout(request, store_id, live_lecture_id):
    """라이브 강의 결제 (무료/유료)"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    live_lecture = get_object_or_404(
        LiveLecture, 
        id=live_lecture_id, 
        store=store, 
        deleted_at__isnull=True
    )
    
    # 라이브 강의 참가 가능 여부 확인
    if not live_lecture.can_participate:
        messages.error(request, '현재 참가 신청이 불가능한 라이브 강의입니다.')
        return redirect('lecture:live_lecture_detail', store_id=store_id, live_lecture_id=live_lecture_id)
    
    # 이미 참가 신청한 사용자인지 확인
    existing_order = LiveLectureOrder.objects.filter(
        live_lecture=live_lecture,
        user=request.user
    ).first()
    
    if existing_order:
        messages.info(request, '이미 참가 신청한 라이브 강의입니다.')
        return redirect('lecture:live_lecture_detail', store_id=store_id, live_lecture_id=live_lecture_id)
    
    # 무료 강의는 바로 신청 완료
    if live_lecture.price_display == 'free':
        with transaction.atomic():
            order = LiveLectureOrder.objects.create(
                live_lecture=live_lecture,
                user=request.user,
                price=0,
                status='confirmed',
                confirmed_at=timezone.now()
            )
            
            messages.success(request, '라이브 강의 참가 신청이 완료되었습니다.')
            return redirect('lecture:live_lecture_checkout_complete', 
                          store_id=store_id, live_lecture_id=live_lecture_id, order_id=order.id)
    
    # 유료 강의는 결제 페이지로
    context = {
        'store': store,
        'live_lecture': live_lecture,
    }
    
    return render(request, 'lecture/lecture_live_checkout.html', context)

def live_lecture_checkout_complete(request, store_id, live_lecture_id, order_id):
    """라이브 강의 신청완료"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    live_lecture = get_object_or_404(
        LiveLecture, 
        id=live_lecture_id, 
        store=store, 
        deleted_at__isnull=True
    )
    order = get_object_or_404(LiveLectureOrder, id=order_id, live_lecture=live_lecture)
    
    # 로그인한 사용자가 아니거나 주문자가 아닌 경우 접근 제한
    if not request.user.is_authenticated or order.user != request.user:
        raise Http404("주문을 찾을 수 없습니다.")
    
    context = {
        'store': store,
        'live_lecture': live_lecture,
        'order': order,
    }
    
    return render(request, 'lecture/lecture_live_checkout_complete.html', context)
