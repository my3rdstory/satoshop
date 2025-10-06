from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Avg, Sum
from django.utils import timezone
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.paginator import Paginator
from django.urls import reverse
from datetime import timedelta

from stores.models import Store
from .models import Lecture, LectureEnrollment, LectureReview, LiveLecture, LiveLectureImage, LiveLectureOrder
from .forms import LiveLectureForm
import json
import logging
from django.conf import settings
from ln_payment.blink_service import get_blink_service_for_store
from ln_payment.models import PaymentTransaction
from ln_payment.services import LightningPaymentProcessor

logger = logging.getLogger(__name__)


class LectureListView(ListView):
    """강의 목록"""
    model = Lecture
    template_name = 'lecture/list.html'
    context_object_name = 'lectures'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Lecture.objects.filter(status='published').select_related('instructor')
        
        # 카테고리 필터 제거됨
            
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
        # 카테고리 관련 컨텍스트 제거됨
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

def browse_live_lectures(request):
    """전체 라이브 강의 둘러보기"""
    from django.core.paginator import Paginator
    
    # 활성화된 모든 라이브 강의 조회 (활성화된 스토어의 것만)
    live_lectures = LiveLecture.objects.filter(
        is_active=True,
        is_temporarily_closed=False,
        deleted_at__isnull=True,
        store__is_active=True,
        store__deleted_at__isnull=True
    ).select_related('store').prefetch_related('images').order_by('-created_at')
    
    # 페이지네이션
    paginator = Paginator(live_lectures, 24)  # 한 페이지에 24개씩
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'live_lectures': page_obj.object_list,
        'page_title': '전체 라이브 강의',
        'page_description': '모든 스토어의 라이브 강의를 한 곳에서 확인하세요',
    }
    
    return render(request, 'lecture/browse_live_lectures.html', context)

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
                    
                    # 원화연동 가격 처리
                    price_display = form.cleaned_data.get('price_display')
                    if price_display == 'krw':
                        # JavaScript에서 계산된 사토시 값 사용
                        price_sats_calculated = request.POST.get('price_sats_calculated')
                        if price_sats_calculated:
                            live_lecture.price = int(price_sats_calculated)
                            logger.info(f"원화연동 가격 처리: {live_lecture.price_krw}원 -> {live_lecture.price}sats")
                    
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
    
    # 먼저 삭제된 강의인지 확인
    try:
        deleted_lecture = LiveLecture.objects.get(
            id=live_lecture_id, 
            store=store, 
            deleted_at__isnull=False
        )
        # 삭제된 강의에 접근한 경우 전용 오류 페이지 표시
        context = {
            'store': store,
            'live_lecture_id': live_lecture_id,
            'deleted_at': deleted_lecture.deleted_at,
            'error_type': 'lecture_deleted'
        }
        return render(request, 'lecture/lecture_not_found.html', context, status=404)
    except LiveLecture.DoesNotExist:
        pass
    
    # 정상적인 강의 조회
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
        logger.info(f"라이브 강의 수정 요청 시작 - ID: {live_lecture_id}")
        logger.info(f"POST 데이터: {dict(request.POST)}")
        
        form = LiveLectureForm(data=request.POST, files=request.FILES, instance=live_lecture)
        logger.info(f"폼 생성 완료 - is_valid() 검사 시작")
        
        if form.is_valid():
            logger.info("폼 검증 성공 - 저장 시작")
            try:
                with transaction.atomic():
                    # 라이브 강의 수정
                    live_lecture = form.save(commit=False)
                    
                    # 원화연동 가격 처리
                    price_display = form.cleaned_data.get('price_display')
                    if price_display == 'krw':
                        # JavaScript에서 계산된 사토시 값 사용
                        price_sats_calculated = request.POST.get('price_sats_calculated')
                        if price_sats_calculated:
                            live_lecture.price = int(price_sats_calculated)
                            logger.info(f"원화연동 가격 처리: {live_lecture.price_krw}원 -> {live_lecture.price}sats")
                    
                    live_lecture.save()
                    
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
                    return redirect('lecture:live_lecture_list', store_id=store_id)
                    
            except Exception as e:
                messages.error(request, '라이브 강의 수정 중 오류가 발생했습니다. 다시 시도해주세요.')
                logger.error(f"Error updating live lecture: {e}", exc_info=True)
        else:
            logger.error(f"LiveLecture 수정 폼 검증 실패 - 에러: {form.errors}")
            messages.error(request, '폼 검증에 실패했습니다. 입력 내용을 확인해주세요.')
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
    
    # 총 매출 및 총 참가자 수 계산
    total_revenue = 0
    total_participants = 0
    
    # 각 라이브 강의별 매출 계산 및 총합 산정
    for live_lecture in live_lectures:
        lecture_revenue = live_lecture.orders.aggregate(
            total=Sum('price')
        )['total'] or 0
        
        # 라이브 강의 객체에 총 매출 추가 (template에서 사용하기 위해)
        live_lecture.total_revenue = lecture_revenue
        total_revenue += lecture_revenue
        total_participants += live_lecture.current_participants
    
    context = {
        'store': store,
        'live_lectures': live_lectures,
        'total_revenue': total_revenue,
        'total_participants': total_participants,
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
    
    # 총 매출 및 참석자 수 계산 (페이지네이션 전 전체 주문에서 계산)
    total_revenue = orders.aggregate(total=Sum('price'))['total'] or 0
    attended_count = orders.filter(attended=True).count()
    attendance_rate = round((attended_count / live_lecture.current_participants * 100) if live_lecture.current_participants > 0 else 0)
    
    # 페이지네이션
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'store': store,
        'live_lecture': live_lecture,
        'orders': page_obj,
        'total_revenue': total_revenue,
        'attended_count': attended_count,
        'attendance_rate': attendance_rate,
    }
    
    return render(request, 'lecture/lecture_live_status_detail.html', context)

@login_required
def live_lecture_manage(request, store_id, live_lecture_id):
    """라이브 강의 관리"""
    store = get_store_with_admin_check(request, store_id)
    if not store:
        return redirect('myshop:home')
    
    live_lecture = get_object_or_404(
        LiveLecture, 
        id=live_lecture_id, 
        store=store, 
        deleted_at__isnull=True
    )
    
    context = {
        'store': store,
        'live_lecture': live_lecture,
        'live_lecture_id': live_lecture_id,
    }
    
    return render(request, 'lecture/lecture_live_manage.html', context)

@login_required
@require_POST
@csrf_exempt
def toggle_live_lecture_temporary_closure(request, store_id, live_lecture_id):
    """라이브 강의 일시중단 토글"""
    import json
    
    try:
        # 스토어 소유자 권한 확인
        store = get_store_with_admin_check(request, store_id)
        if not store:
            return JsonResponse({
                'success': False,
                'error': '권한이 없습니다.'
            })
        live_lecture = get_object_or_404(LiveLecture, id=live_lecture_id, store=store, deleted_at__isnull=True)
        
        # 현재 일시중단 상태 토글
        live_lecture.is_temporarily_closed = not live_lecture.is_temporarily_closed
        live_lecture.save()
        
        action = "일시중단" if live_lecture.is_temporarily_closed else "일시중단 해제"
        message = f'"{live_lecture.name}" 라이브 강의가 {action}되었습니다.'
        
        logger.info(f"라이브 강의 일시중단 상태 변경: {live_lecture.name} - {action} (사용자: {request.user.username})")
        
        return JsonResponse({
            'success': True,
            'message': message,
            'is_temporarily_closed': live_lecture.is_temporarily_closed
        })
        
    except Exception as e:
        logger.error(f"라이브 강의 일시중단 토글 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '일시중단 상태 변경 중 오류가 발생했습니다.'
        })

@login_required
@require_POST
@csrf_exempt
def delete_live_lecture(request, store_id, live_lecture_id):
    """라이브 강의 삭제 (soft delete)"""
    import json
    from django.utils import timezone
    
    try:
        # 스토어 소유자 권한 확인
        store = get_store_with_admin_check(request, store_id)
        if not store:
            return JsonResponse({
                'success': False,
                'error': '권한이 없습니다.'
            })
        
        live_lecture = get_object_or_404(LiveLecture, id=live_lecture_id, store=store, deleted_at__isnull=True)
        
        # 참가자가 있는 경우 삭제 불가
        if live_lecture.current_participants > 0:
            return JsonResponse({
                'success': False,
                'error': '참가자가 있는 라이브 강의는 삭제할 수 없습니다. 먼저 모든 참가자를 취소해주세요.'
            })
        
        # Soft delete 처리
        live_lecture.deleted_at = timezone.now()
        live_lecture.save()
        
        logger.info(f"라이브 강의 삭제: {live_lecture.name} (사용자: {request.user.username})")
        
        return JsonResponse({
            'success': True,
            'message': f'"{live_lecture.name}" 라이브 강의가 성공적으로 삭제되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"라이브 강의 삭제 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '라이브 강의 삭제 중 오류가 발생했습니다.'
        })



def _get_live_lecture_session_key(live_lecture_id: int) -> str:
    return f'live_lecture_participant_data_{live_lecture_id}'


def create_pending_live_lecture_order(live_lecture, participant_data, *, user=None, reservation_seconds: int = 180):
    """결제 진행을 위한 임시 라이브 강의 주문 생성"""
    reservation_expires_at = timezone.now() + timedelta(seconds=reservation_seconds)

    return LiveLectureOrder.objects.create(
        live_lecture=live_lecture,
        user=user,
        price=participant_data['total_price'],
        status='pending',
        is_temporary_reserved=True,
        reservation_expires_at=reservation_expires_at,
        is_early_bird=participant_data.get('is_early_bird', False),
        discount_rate=participant_data.get('discount_rate', 0),
        original_price=participant_data.get('original_price') or None,
    )


def finalize_live_lecture_order_from_transaction(order: LiveLectureOrder, participant_data: dict, *, payment_hash: str = '', payment_request: str = ''):
    """결제 완료 시 임시 라이브 강의 주문을 확정 상태로 전환"""
    order.price = participant_data.get('total_price', order.price)
    order.is_early_bird = participant_data.get('is_early_bird', order.is_early_bird)
    order.discount_rate = participant_data.get('discount_rate', order.discount_rate)
    original_price = participant_data.get('original_price') or None
    if original_price is not None:
        order.original_price = original_price
    order.payment_hash = payment_hash
    order.payment_request = payment_request

    now = timezone.now()
    if not order.paid_at:
        order.paid_at = now
    if not order.confirmed_at:
        order.confirmed_at = now

    order.status = 'confirmed'
    order.is_temporary_reserved = False
    order.auto_cancelled_reason = ''
    order.save(update_fields=[
        'price',
        'is_early_bird',
        'discount_rate',
        'original_price',
        'payment_hash',
        'payment_request',
        'paid_at',
        'confirmed_at',
        'status',
        'is_temporary_reserved',
        'auto_cancelled_reason',
        'updated_at',
    ])

    return order


def serialize_live_lecture_transaction(transaction: PaymentTransaction) -> dict:
    logs = [
        {
            'stage': log.stage,
            'status': log.status,
            'message': log.message,
            'detail': log.detail,
            'created_at': log.created_at.isoformat(),
        }
        for log in transaction.stage_logs.order_by('created_at')
    ]

    payload = {
        'id': str(transaction.id),
        'status': transaction.status,
        'current_stage': transaction.current_stage,
        'payment_hash': transaction.payment_hash,
        'invoice_expires_at': transaction.invoice_expires_at.isoformat() if transaction.invoice_expires_at else None,
        'logs': logs,
        'created_at': transaction.created_at.isoformat(),
        'updated_at': transaction.updated_at.isoformat(),
    }

    if transaction.payment_request:
        payload['invoice'] = {
            'payment_request': transaction.payment_request,
            'payment_hash': transaction.payment_hash,
            'expires_at': transaction.invoice_expires_at.isoformat() if transaction.invoice_expires_at else None,
        }

    if transaction.live_lecture_order:
        payload['live_lecture_order_id'] = transaction.live_lecture_order.id
        payload['order_number'] = transaction.live_lecture_order.order_number

    if transaction.order:
        payload['order_number'] = transaction.order.order_number

    return payload


def build_live_lecture_invoice_memo(live_lecture: LiveLecture, participant_data: dict, user) -> str:
    participant_name = participant_data.get('participant_name') or getattr(user, 'username', '') or '참가자'
    amount = participant_data.get('total_price', live_lecture.current_price)
    payer_identifier = getattr(user, 'username', None) or getattr(user, 'email', None) or str(getattr(user, 'id', 'user'))

    lecture_time = ''
    if live_lecture.date_time:
        lecture_time = timezone.localtime(live_lecture.date_time).strftime('%m/%d %H:%M')

    memo_parts = [
        live_lecture.name,
        f"참가자 {participant_name}",
        f"금액 {amount} sats",
        f"결제자 {payer_identifier}",
    ]

    if lecture_time:
        memo_parts.insert(1, f"강의 {lecture_time}")

    memo = ' / '.join(memo_parts)
    return memo[:620] + '…' if len(memo) > 620 else memo



@login_required
def live_lecture_checkout(request, store_id, live_lecture_id):
    """라이브 강의 결제 (무료/유료)"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    live_lecture = get_object_or_404(
        LiveLecture,
        id=live_lecture_id,
        store=store,
        deleted_at__isnull=True,
    )

    if settings.DEBUG:
        logger.debug(
            "라이브 강의 체크아웃 접근 - 사용자: %s, 강의: %s",
            request.user,
            live_lecture.name,
        )
        logger.debug(
            "라이브 강의 상태 - active=%s, temp_closed=%s, expired=%s, full=%s",
            live_lecture.is_active,
            live_lecture.is_temporarily_closed,
            live_lecture.is_expired,
            live_lecture.is_full,
        )

    if not live_lecture.can_participate:
        messages.error(request, '현재 참가 신청이 불가능한 라이브 강의입니다.')
        return redirect('lecture:live_lecture_detail', store_id=store_id, live_lecture_id=live_lecture_id)

    existing_order = LiveLectureOrder.objects.filter(
        live_lecture=live_lecture,
        user=request.user,
        status__in=['confirmed', 'completed'],
    ).first()

    if existing_order and live_lecture.price_display != 'free' and not existing_order.paid_at:
        existing_order = None

    if existing_order:
        messages.info(
            request,
            f'이미 참가 신청이 완료된 라이브 강의입니다. (주문번호: {existing_order.order_number})',
        )
        return redirect(
            'lecture:live_lecture_checkout_complete',
            store_id=store_id,
            live_lecture_id=live_lecture_id,
            order_id=existing_order.id,
        )

    session_key = _get_live_lecture_session_key(live_lecture_id)
    participant_data = request.session.get(session_key, {})

    full_name = getattr(request.user, 'get_full_name', None)
    if callable(full_name):
        full_name = full_name()
    participant_name = (full_name or request.user.username or '').strip()
    if not participant_name:
        participant_name = (getattr(request.user, 'email', '') or '').strip()
    participant_name = participant_name or '참가자'

    participant_email = (getattr(request.user, 'email', '') or '').strip()

    base_price = int(live_lecture.current_price or 0)

    participant_data.update({
        'participant_name': participant_data.get('participant_name') or participant_name,
        'participant_email': participant_email,
        'participant_phone': participant_data.get('participant_phone', ''),
        'base_price': base_price,
        'options_price': 0,
        'total_price': base_price,
        'is_early_bird': live_lecture.is_early_bird_active,
        'discount_rate': live_lecture.public_discount_rate,
    })

    if live_lecture.is_discounted and live_lecture.is_early_bird_active:
        if live_lecture.price_display == 'krw':
            original_price = live_lecture.public_price_krw
        else:
            original_price = live_lecture.price
        participant_data['original_price'] = original_price or base_price
    else:
        participant_data['original_price'] = participant_data.get('original_price') or None

    request.session[session_key] = participant_data

    total_price = int(participant_data.get('total_price', 0))

    if request.method == 'POST' and total_price == 0:
        try:
            with transaction.atomic():
                order = LiveLectureOrder.objects.create(
                    live_lecture=live_lecture,
                    user=request.user,
                    price=0,
                    status='confirmed',
                    confirmed_at=timezone.now(),
                    paid_at=timezone.now(),
                    is_temporary_reserved=False,
                    is_early_bird=participant_data.get('is_early_bird', False),
                    discount_rate=participant_data.get('discount_rate', 0),
                    original_price=participant_data.get('original_price') or None,
                )
            try:
                from .services import send_live_lecture_notification_email

                send_live_lecture_notification_email(order)
            except Exception:  # pylint: disable=broad-except
                logger.exception('라이브 강의 무료 참가 알림 실패 order=%s', order.id)
            request.session.pop(session_key, None)
            messages.success(request, '라이브 강의 참가 신청이 완료되었습니다.')
            return redirect(
                'lecture:live_lecture_checkout_complete',
                store_id=store_id,
                live_lecture_id=live_lecture_id,
                order_id=order.id,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.error('무료 라이브 강의 주문 생성 실패: %s', exc)
            messages.error(request, '참가 신청 중 오류가 발생했습니다. 다시 시도해주세요.')

    try:
        payment_service_available = get_blink_service_for_store(store) is not None
    except Exception:  # pylint: disable=broad-except
        payment_service_available = False

    from myshop.models import SiteSettings

    site_settings = SiteSettings.get_settings()
    countdown_seconds = site_settings.meetup_countdown_seconds
    placeholder_uuid = '11111111-1111-1111-1111-111111111111'

    transaction_payload = None
    transaction_id = participant_data.get('transaction_id')
    if transaction_id:
        try:
            existing_transaction = PaymentTransaction.objects.select_related('live_lecture_order').get(
                id=transaction_id,
                user=request.user,
                store=store,
            )
            transaction_payload = serialize_live_lecture_transaction(existing_transaction)
        except (PaymentTransaction.DoesNotExist, ValueError):
            transaction_payload = None

    context = {
        'store': store,
        'live_lecture': live_lecture,
        'participant_data': participant_data,
        'payment_service_available': payment_service_available,
        'countdown_seconds': countdown_seconds,
        'workflow_start_url': reverse('lecture:live_lecture_start_payment_workflow', args=[store_id, live_lecture_id]),
        'workflow_status_url_template': reverse('lecture:live_lecture_payment_status', args=[store_id, live_lecture_id, placeholder_uuid]),
        'workflow_verify_url_template': reverse('lecture:live_lecture_verify_payment', args=[store_id, live_lecture_id, placeholder_uuid]),
        'workflow_cancel_url_template': reverse('lecture:live_lecture_cancel_payment', args=[store_id, live_lecture_id, placeholder_uuid]),
        'workflow_inventory_redirect_url': reverse('lecture:live_lecture_detail', args=[store_id, live_lecture_id]),
        'workflow_cart_url': reverse('lecture:live_lecture_detail', args=[store_id, live_lecture_id]),
        'placeholder_uuid': placeholder_uuid,
        'existing_transaction': transaction_payload,
        'total_price': total_price,
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

@login_required 
def live_lecture_orders(request, store_id):
    """사용자의 라이브 강의 주문 내역"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    
    # 해당 스토어의 라이브 강의에 대한 사용자 주문 내역
    orders = LiveLectureOrder.objects.filter(
        live_lecture__store=store,
        user=request.user
    ).select_related('live_lecture', 'user').order_by('-created_at')
    
    # 페이지네이션
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'store': store,
        'orders': page_obj,
    }
    
    return render(request, 'lecture/lecture_live_orders.html', context)

@login_required
def export_live_lecture_participants_csv(request, store_id, live_lecture_id):
    """라이브 강의 참가자 목록 CSV 다운로드"""
    import csv
    from django.http import HttpResponse
    from datetime import datetime
    
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
    
    # CSV 응답 생성
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    exported_at = timezone.localtime(timezone.now())
    response['Content-Disposition'] = (
        f'attachment; filename="라이브강의_참가자_{live_lecture.name}_{exported_at.strftime("%Y%m%d")}.csv"'
    )
    
    # BOM 추가 (Excel에서 한글 깨짐 방지)
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # 헤더 작성
    headers = [
        '참가자명', '이메일', '참가비', '주문번호', 
        '참가신청일시', '결제완료일시', '상태'
    ]
    if live_lecture.price_display != 'free':
        headers.append('결제해시')
    
    writer.writerow(headers)
    
    # 데이터 작성
    for order in orders:
        row = [
            order.user.username,
            order.user.email,
            f"{order.price} sats" if order.price > 0 else "무료",
            order.order_number,
            timezone.localtime(order.created_at).strftime('%Y-%m-%d %H:%M:%S'),
            timezone.localtime(order.paid_at).strftime('%Y-%m-%d %H:%M:%S') if order.paid_at else '',
            '참가확정' if order.status == 'confirmed' else '신청완료' if order.status == 'completed' else '취소됨'
        ]
        
        if live_lecture.price_display != 'free':
            row.append(order.payment_hash if hasattr(order, 'payment_hash') and order.payment_hash else '')
        
        writer.writerow(row)
    
    return response

@login_required
def live_lecture_order_complete(request, store_id, live_lecture_id, order_id):
    """라이브 강의 주문 확정서 (주문 내역에서 접근)"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    live_lecture = get_object_or_404(
        LiveLecture, 
        id=live_lecture_id, 
        store=store, 
        deleted_at__isnull=True
    )
    order = get_object_or_404(LiveLectureOrder, id=order_id, live_lecture=live_lecture)
    
    # 로그인한 사용자가 주문자인지 확인
    if order.user != request.user:
        messages.error(request, '접근 권한이 없습니다.')
        return redirect('lecture:live_lecture_list', store_id=store_id)
    
    context = {
        'store': store,
        'live_lecture': live_lecture,
        'order': order,
    }
    
    return render(request, 'lecture/lecture_live_checkout_complete.html', context)


@login_required
@require_POST
def live_lecture_start_payment_workflow(request, store_id, live_lecture_id):
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    live_lecture = get_object_or_404(
        LiveLecture,
        id=live_lecture_id,
        store=store,
        deleted_at__isnull=True,
        is_active=True,
    )

    if not live_lecture.can_participate:
        return JsonResponse({'success': False, 'error': '현재 참가 신청이 불가능합니다.'}, status=409)

    session_key = _get_live_lecture_session_key(live_lecture_id)
    participant_data = request.session.get(session_key)
    if not participant_data:
        return JsonResponse({'success': False, 'error': '참가자 정보가 없습니다.'}, status=400)

    amount_sats = int(participant_data.get('total_price', 0))
    if amount_sats <= 0:
        return JsonResponse({'success': False, 'error': '결제 금액이 올바르지 않습니다.'}, status=400)

    from myshop.models import SiteSettings

    site_settings = SiteSettings.get_settings()
    reservation_seconds = max(120, site_settings.meetup_countdown_seconds)
    soft_lock_minutes = max(1, (reservation_seconds + 59) // 60)

    processor = LightningPaymentProcessor(store)

    previous_transaction_id = participant_data.get('transaction_id')
    if previous_transaction_id:
        try:
            previous_transaction = PaymentTransaction.objects.select_related('live_lecture_order').get(
                id=previous_transaction_id,
                user=request.user,
                store=store,
            )
            if previous_transaction.status != PaymentTransaction.STATUS_COMPLETED:
                processor.cancel_transaction(previous_transaction, '라이브 강의 결제 재시작', detail={'reason': 'restart'})
                if previous_transaction.live_lecture_order and previous_transaction.live_lecture_order.status == 'pending':
                    order = previous_transaction.live_lecture_order
                    order.status = 'cancelled'
                    order.is_temporary_reserved = False
                    order.auto_cancelled_reason = '라이브 강의 결제 재시작'
                    order.save(update_fields=[
                        'status',
                        'is_temporary_reserved',
                        'auto_cancelled_reason',
                        'updated_at',
                    ])
        except (PaymentTransaction.DoesNotExist, ValueError):
            pass
        participant_data.pop('transaction_id', None)
        participant_data.pop('payment_hash', None)
        participant_data.pop('payment_request', None)
        participant_data.pop('live_lecture_order_id', None)

    try:
        with transaction.atomic():
            locked_live_lecture = LiveLecture.objects.select_for_update().get(
                id=live_lecture.id,
                store=store,
                deleted_at__isnull=True,
            )
            if locked_live_lecture.max_participants and locked_live_lecture.current_participants >= locked_live_lecture.max_participants:
                return JsonResponse({'success': False, 'error': '라이브 강의 정원이 가득 찼습니다.'}, status=409)

            pending_order = create_pending_live_lecture_order(
                locked_live_lecture,
                participant_data,
                user=request.user,
                reservation_seconds=reservation_seconds,
            )

        transaction = processor.create_transaction(
            user=request.user,
            amount_sats=amount_sats,
            currency='BTC',
            cart_items=None,
            soft_lock_ttl_minutes=soft_lock_minutes,
            metadata={
                'participant': participant_data,
                'live_lecture_id': live_lecture.id,
                'live_lecture_order_id': pending_order.id,
            },
            prepare_message='라이브 강의 참가 정보 확인 완료',
            prepare_detail={
                'live_lecture_order_id': pending_order.id,
                'reservation_expires_at': pending_order.reservation_expires_at.isoformat() if pending_order.reservation_expires_at else None,
                'amount_sats': amount_sats,
            },
        )
        transaction.live_lecture_order = pending_order
        transaction.save(update_fields=['live_lecture_order', 'updated_at'])

        invoice = processor.issue_invoice(
            transaction,
            memo=build_live_lecture_invoice_memo(live_lecture, participant_data, request.user),
            expires_in_minutes=max(1, min(soft_lock_minutes, 15)),
        )
    except ValueError as exc:
        logger.warning('라이브 강의 결제 준비 실패: %s', exc)
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception('라이브 강의 결제 준비 중 오류')
        return JsonResponse({'success': False, 'error': '결제 준비 중 오류가 발생했습니다.'}, status=500)

    participant_data['transaction_id'] = str(transaction.id)
    participant_data['live_lecture_order_id'] = pending_order.id
    participant_data['payment_hash'] = invoice['payment_hash']
    participant_data['payment_request'] = invoice['invoice']
    request.session[session_key] = participant_data

    return JsonResponse({
        'success': True,
        'transaction': serialize_live_lecture_transaction(transaction),
        'invoice': {
            'payment_hash': invoice['payment_hash'],
            'payment_request': invoice['invoice'],
            'expires_at': invoice.get('expires_at').isoformat() if invoice.get('expires_at') else None,
        },
        'reservation_expires_at': pending_order.reservation_expires_at.isoformat() if pending_order.reservation_expires_at else None,
    })


@login_required
@require_http_methods(['GET'])
def live_lecture_payment_status(request, store_id, live_lecture_id, transaction_id):
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    get_object_or_404(
        LiveLecture,
        id=live_lecture_id,
        store=store,
        deleted_at__isnull=True,
    )

    try:
        transaction = PaymentTransaction.objects.select_related('live_lecture_order').get(
            id=transaction_id,
            user=request.user,
            store=store,
        )
    except (PaymentTransaction.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'error': '결제 정보를 찾을 수 없습니다.'}, status=404)

    payload = serialize_live_lecture_transaction(transaction)
    payload['live_lecture_id'] = live_lecture_id

    return JsonResponse({'success': True, 'transaction': payload})


@login_required
@require_POST
def live_lecture_verify_payment(request, store_id, live_lecture_id, transaction_id):
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    live_lecture = get_object_or_404(
        LiveLecture,
        id=live_lecture_id,
        store=store,
        deleted_at__isnull=True,
    )

    try:
        transaction = PaymentTransaction.objects.select_related('live_lecture_order').get(
            id=transaction_id,
            user=request.user,
            store=store,
        )
    except (PaymentTransaction.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'error': '결제 정보를 찾을 수 없습니다.'}, status=404)

    processor = LightningPaymentProcessor(store)

    try:
        status_result = processor.check_user_payment(transaction)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception('라이브 강의 결제 상태 확인 실패 transaction=%s', transaction_id)
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)

    status_value = status_result.get('status')
    session_key = _get_live_lecture_session_key(live_lecture_id)
    participant_data = transaction.metadata.get('participant') if isinstance(transaction.metadata, dict) else None
    if not participant_data:
        participant_data = request.session.get(session_key, {})

    if status_value == 'expired':
        processor.cancel_transaction(transaction, '인보이스 만료', detail=status_result)
        if transaction.live_lecture_order and transaction.live_lecture_order.status == 'pending':
            order = transaction.live_lecture_order
            order.status = 'cancelled'
            order.is_temporary_reserved = False
            order.auto_cancelled_reason = '인보이스 만료'
            order.save(update_fields=[
                'status',
                'is_temporary_reserved',
                'auto_cancelled_reason',
                'updated_at',
            ])
        session_data = request.session.get(session_key, {})
        session_data.pop('transaction_id', None)
        session_data.pop('payment_hash', None)
        session_data.pop('payment_request', None)
        session_data.pop('live_lecture_order_id', None)
        request.session[session_key] = session_data
        return JsonResponse({
            'success': False,
            'error': '인보이스가 만료되었습니다.',
            'transaction': serialize_live_lecture_transaction(transaction),
        }, status=400)

    if status_value != 'paid':
        return JsonResponse({
            'success': True,
            'status': status_value,
            'transaction': serialize_live_lecture_transaction(transaction),
        })

    live_lecture_order = transaction.live_lecture_order
    if not live_lecture_order and isinstance(transaction.metadata, dict):
        live_lecture_order_id = transaction.metadata.get('live_lecture_order_id')
        if live_lecture_order_id:
            live_lecture_order = LiveLectureOrder.objects.filter(id=live_lecture_order_id).first()

    if not live_lecture_order:
        return JsonResponse({'success': False, 'error': '주문 정보를 찾을 수 없습니다.'}, status=500)

    participant_data['payment_hash'] = transaction.payment_hash
    participant_data['payment_request'] = transaction.payment_request

    finalize_live_lecture_order_from_transaction(
        live_lecture_order,
        participant_data,
        payment_hash=transaction.payment_hash,
        payment_request=transaction.payment_request,
    )

    settlement_payload = {'status': status_result.get('raw_status'), 'provider': 'blink'}
    processor.mark_settlement(transaction, tx_payload=settlement_payload)
    processor.finalize_live_lecture_order(transaction, live_lecture_order)

    try:
        from .services import (
            send_live_lecture_notification_email,
            send_live_lecture_participant_confirmation_email,
        )

        send_live_lecture_notification_email(live_lecture_order)
        send_live_lecture_participant_confirmation_email(live_lecture_order)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error('라이브 강의 결제 이메일 발송 실패 - order_id=%s, error=%s', live_lecture_order.id, exc)

    request.session.pop(session_key, None)

    redirect_url = reverse(
        'lecture:live_lecture_checkout_complete',
        args=[store_id, live_lecture_id, live_lecture_order.id],
    )

    payload = serialize_live_lecture_transaction(transaction)
    payload['redirect_url'] = redirect_url

    return JsonResponse({
        'success': True,
        'status': status_value,
        'transaction': payload,
        'order': {
            'id': live_lecture_order.id,
            'order_number': live_lecture_order.order_number,
            'price': live_lecture_order.price,
        },
        'redirect_url': redirect_url,
    })


@login_required
@require_POST
def live_lecture_cancel_payment(request, store_id, live_lecture_id, transaction_id):
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        payload = {}

    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)

    try:
        transaction = PaymentTransaction.objects.select_related('live_lecture_order').get(
            id=transaction_id,
            user=request.user,
            store=store,
        )
    except (PaymentTransaction.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'error': '결제 정보를 찾을 수 없습니다.'}, status=404)

    processor = LightningPaymentProcessor(store)
    processor.cancel_transaction(transaction, '사용자 취소', detail=payload)

    if transaction.live_lecture_order and transaction.live_lecture_order.status == 'pending':
        order = transaction.live_lecture_order
        order.status = 'cancelled'
        order.is_temporary_reserved = False
        order.auto_cancelled_reason = '사용자 취소'
        order.save(update_fields=[
            'status',
            'is_temporary_reserved',
            'auto_cancelled_reason',
            'updated_at',
        ])

    session_key = _get_live_lecture_session_key(live_lecture_id)
    session_data = request.session.get(session_key, {})
    session_data.pop('transaction_id', None)
    session_data.pop('payment_hash', None)
    session_data.pop('payment_request', None)
    session_data.pop('live_lecture_order_id', None)
    request.session[session_key] = session_data

    return JsonResponse({'success': True, 'transaction': serialize_live_lecture_transaction(transaction)})


@login_required
def debug_live_lecture_participation(request, store_id, live_lecture_id):
    """라이브 강의 참가 가능 여부 디버깅용 뷰"""
    store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
    live_lecture = get_object_or_404(
        LiveLecture, 
        id=live_lecture_id, 
        store=store, 
        deleted_at__isnull=True
    )
    
    debug_info = {
        'live_lecture_name': live_lecture.name,
        'is_active': live_lecture.is_active,
        'is_temporarily_closed': live_lecture.is_temporarily_closed,
        'is_expired': live_lecture.is_expired,
        'is_full': live_lecture.is_full,
        'can_participate': live_lecture.can_participate,
        'current_participants': live_lecture.current_participants,
        'max_participants': live_lecture.max_participants,
        'no_limit': live_lecture.no_limit,
        'date_time': live_lecture.date_time,
        'current_time': timezone.now(),
        'existing_order': LiveLectureOrder.objects.filter(
            live_lecture=live_lecture,
            user=request.user
        ).exists()
    }
    
    return JsonResponse(debug_info, json_dumps_params={'default': str})

@login_required
@require_POST
@csrf_exempt
def update_live_lecture_attendance(request, store_id, live_lecture_id):
    """라이브 강의 참석 여부 업데이트"""
    import json
    from django.utils import timezone
    
    try:
        # 스토어 소유자 권한 확인
        store = get_store_with_admin_check(request, store_id)
        if not store:
            return JsonResponse({
                'success': False,
                'error': '권한이 없습니다.'
            })
        live_lecture = get_object_or_404(LiveLecture, id=live_lecture_id, store=store, deleted_at__isnull=True)
        
        data = json.loads(request.body)
        order_id = data.get('order_id')
        attended = data.get('attended', False)
        
        if not order_id:
            return JsonResponse({
                'success': False,
                'error': '주문 ID가 필요합니다.'
            })
        
        # 해당 라이브 강의의 주문인지 확인
        order = get_object_or_404(
            LiveLectureOrder,
            id=order_id,
            live_lecture=live_lecture,
            status__in=['confirmed', 'completed']
        )
        
        # 참석 여부 업데이트
        order.attended = attended
        if attended:
            order.attended_at = timezone.now()
        else:
            order.attended_at = None
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': '참석 여부가 업데이트되었습니다.',
            'attended': order.attended,
            'attended_at': order.attended_at.isoformat() if order.attended_at else None
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '잘못된 요청 형식입니다.'
        })
    except Exception as e:
        logger.error(f"라이브 강의 참석 여부 업데이트 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '참석 여부 업데이트 중 오류가 발생했습니다.'
        })

@login_required
@require_POST
@csrf_exempt
def cancel_live_lecture_participation(request, store_id, live_lecture_id):
    """라이브 강의 참가 취소"""
    import json
    from django.utils import timezone
    
    try:
        # 스토어 소유자 권한 확인
        store = get_store_with_admin_check(request, store_id)
        if not store:
            return JsonResponse({
                'success': False,
                'error': '권한이 없습니다.'
            })
        live_lecture = get_object_or_404(LiveLecture, id=live_lecture_id, store=store, deleted_at__isnull=True)
        
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        if not order_id:
            return JsonResponse({
                'success': False,
                'error': '주문 ID가 필요합니다.'
            })
        
        # 해당 라이브 강의의 확정된 주문인지 확인
        order = get_object_or_404(
            LiveLectureOrder,
            id=order_id,
            live_lecture=live_lecture,
            status='confirmed'
        )
        
        # 주문 상태를 취소로 변경
        order.status = 'cancelled'
        order.save()
        
        logger.info(f"라이브 강의 참가 취소: {order.order_number}")
        
        return JsonResponse({
            'success': True,
            'message': '참가가 성공적으로 취소되었습니다.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '잘못된 요청 형식입니다.'
        })
    except Exception as e:
        logger.error(f"라이브 강의 참가 취소 오류: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': '참가 취소 중 오류가 발생했습니다.'
        })
