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

from stores.models import Store
from .models import Lecture, LectureEnrollment, LectureReview, LiveLecture, LiveLectureImage, LiveLectureOrder
from .forms import LiveLectureForm
import json
import logging
from django.conf import settings
from ln_payment.blink_service import get_blink_service_for_store

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
    
    # 🐛 디버깅: 라이브 강의 상태 로그
    if settings.DEBUG:
        logger.debug(f"라이브 강의 체크아웃 접근 - 사용자: {request.user}, 강의: {live_lecture.name}")
        logger.debug(f"라이브 강의 상태 - is_active: {live_lecture.is_active}, is_temporarily_closed: {live_lecture.is_temporarily_closed}, is_expired: {live_lecture.is_expired}, is_full: {live_lecture.is_full}")
        logger.debug(f"can_participate: {live_lecture.can_participate}")
    
    # 라이브 강의 참가 가능 여부 확인
    if not live_lecture.can_participate:
        if settings.DEBUG:
            logger.debug(f"참가 불가능 - is_active: {live_lecture.is_active}, is_temporarily_closed: {live_lecture.is_temporarily_closed}, is_expired: {live_lecture.is_expired}, is_full: {live_lecture.is_full}")
        messages.error(request, '현재 참가 신청이 불가능한 라이브 강의입니다.')
        return redirect('lecture:live_lecture_detail', store_id=store_id, live_lecture_id=live_lecture_id)
    
    # 이미 참가 신청한 사용자인지 확인 (취소된 주문은 제외)
    # 🔍 실제로 결제 완료된 주문만 확인 (유료 강의의 경우 paid_at 필수)
    existing_order = LiveLectureOrder.objects.filter(
        live_lecture=live_lecture,
        user=request.user,
        status__in=['confirmed', 'completed']
    ).first()
    
    # 유료 강의의 경우 실제 결제 완료 여부도 확인
    if existing_order and live_lecture.price_display != 'free':
        if not existing_order.paid_at:
            # 결제되지 않은 주문은 무시 (결제 취소된 경우)
            if settings.DEBUG:
                logger.debug(f"결제되지 않은 기존 주문 발견 - 주문 ID: {existing_order.id}, 무시하고 계속 진행")
            existing_order = None
    
    if existing_order:
        if settings.DEBUG:
            logger.debug(f"이미 참가 신청한 사용자 - 주문 ID: {existing_order.id}, 상태: {existing_order.status}, 결제여부: {existing_order.paid_at is not None}")
        
        # 기존 참가 확정 주문이 있으면 확정서 페이지로 이동
        messages.info(request, f'이미 참가 신청이 완료된 라이브 강의입니다. (주문번호: {existing_order.order_number})')
        return redirect('lecture:live_lecture_checkout_complete', 
                       store_id=store_id, live_lecture_id=live_lecture_id, order_id=existing_order.id)
    
    # 무료 강의는 바로 신청 완료
    if live_lecture.price_display == 'free':
        with transaction.atomic():
            try:
                order = LiveLectureOrder.objects.create(
                    live_lecture=live_lecture,
                    user=request.user,
                    price=0,
                    status='confirmed',
                    confirmed_at=timezone.now(),
                    paid_at=timezone.now()
                )
            except Exception as e:
                # 중복 신청 시도 시 기존 주문으로 리다이렉트
                if 'unique_active_live_lecture_order_per_user' in str(e):
                    existing_order = LiveLectureOrder.objects.filter(
                        live_lecture=live_lecture,
                        user=request.user,
                        status__in=['confirmed', 'completed']
                        # 무료 강의는 paid_at이 없을 수 있으므로 별도 조건 없음
                    ).first()
                    if existing_order:
                        messages.info(request, f'이미 참가 신청이 완료된 라이브 강의입니다. (주문번호: {existing_order.order_number})')
                        return redirect('lecture:live_lecture_checkout_complete', 
                                       store_id=store_id, live_lecture_id=live_lecture_id, order_id=existing_order.id)
                # 다른 에러는 다시 발생시킴
                raise e
            
            # 주최자에게 알림 이메일 발송
            try:
                from .services import send_live_lecture_notification_email
                send_live_lecture_notification_email(order)
            except Exception:
                pass  # 이메일 발송 실패는 무시하고 진행
            
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
def create_live_lecture_invoice(request, store_id, live_lecture_id):
    """라이브 강의 결제 인보이스 생성"""
    try:
        if settings.DEBUG:
            logger.debug(f"create_live_lecture_invoice 호출 - User: {request.user}, Store: {store_id}, Lecture: {live_lecture_id}")
        
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        live_lecture = get_object_or_404(
            LiveLecture, 
            id=live_lecture_id, 
            store=store, 
            deleted_at__isnull=True
        )
        
        # 라이브 강의 참가 가능 여부 확인
        if not live_lecture.can_participate:
            return JsonResponse({
                'success': False, 
                'error': '현재 참가 신청이 불가능한 라이브 강의입니다.'
            }, status=400)
        
        # 이미 참가 신청한 사용자인지 확인 (실제 결제 완료된 주문만)
        existing_order = LiveLectureOrder.objects.filter(
            live_lecture=live_lecture,
            user=request.user,
            status__in=['confirmed', 'completed'],
            paid_at__isnull=False  # 실제 결제 완료된 주문만 확인
        ).first()
        
        if existing_order:
            return JsonResponse({
                'success': False, 
                'error': '이미 참가 신청한 라이브 강의입니다.'
            }, status=400)
        
        # 🧹 기존 세션 데이터 정리 (새로운 결제를 위해)
        session_key = f'live_lecture_participant_data_{live_lecture_id}'
        if session_key in request.session:
            del request.session[session_key]
            logger.debug(f"기존 세션 데이터 정리 - live_lecture_id: {live_lecture_id}")
        
        # 무료 강의는 인보이스 생성 불가
        if live_lecture.price_display == 'free':
            return JsonResponse({
                'success': False, 
                'error': '무료 강의는 결제가 필요하지 않습니다.'
            }, status=400)
        
        # BlinkAPIService 초기화
        try:
            blink_service = get_blink_service_for_store(store)
            if settings.DEBUG:
                logger.debug("BlinkAPIService 초기화 성공")
        except Exception as e:
            if settings.DEBUG:
                logger.error(f"BlinkAPIService 초기화 실패: {str(e)}")
            return JsonResponse({
                'success': False, 
                'error': f'결제 서비스 초기화 실패: {str(e)}'
            }, status=500)
        
        # 인보이스 생성
        amount_sats = live_lecture.current_price
        memo = f"{live_lecture.name} - {store.store_name}"
        
        if settings.DEBUG:
            logger.debug(f"인보이스 생성 시작: amount={amount_sats} sats, memo={memo}")
        
        result = blink_service.create_invoice(
            amount_sats=amount_sats,
            memo=memo,
            expires_in_minutes=15
        )
        
        if settings.DEBUG:
            logger.debug(f"인보이스 생성 결과: {result}")
        
        if not result['success']:
            return JsonResponse({
                'success': False,
                'error': result['error']
            }, status=500)
        
        # 🔄 밋업과 동일: 세션에 참가자 정보 저장 (DB에 주문 생성하지 않음)
        participant_data = {
            'live_lecture_id': live_lecture_id,
            'participant_name': request.user.username,
            'participant_email': request.user.email,
            'price': amount_sats,
            'payment_hash': result['payment_hash'],
            'payment_request': result['invoice'],
            'expires_at': result['expires_at'].isoformat() if result.get('expires_at') else None,
        }
        
        # 세션에 참가자 정보 저장 (결제 완료 시 사용)
        request.session[f'live_lecture_participant_data_{live_lecture_id}'] = participant_data
        
        if settings.DEBUG:
            logger.debug(f"세션에 참가자 정보 저장 완료")
        
        # 응답 데이터 준비
        response_data = {
            'success': True,
            'payment_hash': result['payment_hash'],
            'invoice': result['invoice'],
            'amount': amount_sats,
            'memo': memo,
            'expires_at': result['expires_at'].isoformat() if result.get('expires_at') else None,
        }
        
        if settings.DEBUG:
            logger.debug(f"응답 데이터: {response_data}")
        return JsonResponse(response_data)
        
    except Exception as e:
        if settings.DEBUG:
            logger.error(f"인보이스 생성 중 오류: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'인보이스 생성 중 오류가 발생했습니다: {str(e)}'
        }, status=500)

@login_required 
@require_POST
def check_live_lecture_payment(request, store_id, live_lecture_id):
    """라이브 강의 결제 상태 확인"""
    try:
        data = json.loads(request.body)
        payment_hash = data.get('payment_hash')
        
        if not payment_hash:
            return JsonResponse({
                'success': False, 
                'error': '결제 해시가 필요합니다.'
            }, status=400)
        
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        live_lecture = get_object_or_404(
            LiveLecture, 
            id=live_lecture_id, 
            store=store, 
            deleted_at__isnull=True
        )
        
        # 🔄 밋업과 동일: 세션에서 참가자 정보 확인
        participant_data = request.session.get(f'live_lecture_participant_data_{live_lecture_id}')
        if not participant_data:
            return JsonResponse({
                'success': False,
                'error': '참가자 정보가 없습니다.'
            })
        
        stored_payment_hash = participant_data.get('payment_hash')
        if not stored_payment_hash or stored_payment_hash != payment_hash:
            return JsonResponse({
                'success': False,
                'error': '결제 정보가 일치하지 않습니다.'
            })
        
        # 🛡️ 중복 주문 생성 방지: 이미 해당 payment_hash로 주문이 존재하는지 확인
        existing_orders = LiveLectureOrder.objects.filter(
            payment_hash=payment_hash,
            paid_at__isnull=False  # 실제 결제 완료된 주문만 확인
        )
        if existing_orders.exists():
            logger.debug(f"이미 결제 완료된 주문 발견: {payment_hash}")
            order = existing_orders.first()
            return JsonResponse({
                'success': True,
                'status': 'paid',
                'order_id': order.id
            })
        
        # BlinkAPIService 초기화
        blink_service = get_blink_service_for_store(store)
        
        # 결제 상태 확인
        result = blink_service.check_invoice_status(payment_hash)
        
        if not result['success']:
            return JsonResponse({
                'success': False,
                'error': result['error']
            }, status=500)
        
        status = result['status']
        
        # 🔄 밋업과 동일: 결제 완료 시에만 주문 생성
        if status == 'paid':
            logger.info(f"결제 완료 감지 - live_lecture_id: {live_lecture_id}, payment_hash: {payment_hash}")
            
            with transaction.atomic():
                try:
                    # 주문 생성
                    order = LiveLectureOrder.objects.create(
                        live_lecture=live_lecture,
                        user=request.user,
                        price=participant_data['price'],
                        status='confirmed',
                        payment_hash=payment_hash,
                        payment_request=participant_data['payment_request'],
                        paid_at=timezone.now(),
                        confirmed_at=timezone.now(),
                        is_temporary_reserved=False
                    )
                    
                    logger.info(f"주문 생성 완료 - order_id: {order.id}, 주문번호: {order.order_number}")
                except Exception as e:
                    # 중복 신청 시도 시 기존 주문 확인
                    if 'unique_active_live_lecture_order_per_user' in str(e):
                        existing_order = LiveLectureOrder.objects.filter(
                            live_lecture=live_lecture,
                            user=request.user,
                            status__in=['confirmed', 'completed'],
                            paid_at__isnull=False  # 실제 결제 완료된 주문만 확인
                        ).first()
                        if existing_order:
                            logger.warning(f"중복 신청 시도 감지, 기존 주문으로 처리 - existing_order_id: {existing_order.id}")
                            order = existing_order
                        else:
                            raise e
                    else:
                        raise e
            
            # 세션에서 참가자 정보 삭제 (주문 생성 완료)
            if f'live_lecture_participant_data_{live_lecture_id}' in request.session:
                del request.session[f'live_lecture_participant_data_{live_lecture_id}']
            
            # 주최자에게 알림 이메일 발송
            try:
                from .services import send_live_lecture_notification_email
                send_live_lecture_notification_email(order)
            except Exception:
                pass  # 이메일 발송 실패는 무시하고 진행
        
        return JsonResponse({
            'success': True,
            'status': status,
            'order_id': order.id if status == 'paid' else None
        })
        
    except Exception as e:
        logger.error(f"결제 상태 확인 중 오류: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'결제 상태 확인 중 오류가 발생했습니다: {str(e)}'
        }, status=500)

@login_required
@require_POST  
def cancel_live_lecture_payment(request, store_id, live_lecture_id):
    """라이브 강의 결제 취소"""
    try:
        data = json.loads(request.body)
        payment_hash = data.get('payment_hash')
        
        if not payment_hash:
            return JsonResponse({
                'success': False, 
                'error': '결제 해시가 필요합니다.'
            }, status=400)
        
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        live_lecture = get_object_or_404(
            LiveLecture, 
            id=live_lecture_id, 
            store=store, 
            deleted_at__isnull=True
        )
        
        # 🔄 밋업과 동일: 세션에서 참가자 정보 확인
        participant_data = request.session.get(f'live_lecture_participant_data_{live_lecture_id}')
        if not participant_data:
            return JsonResponse({
                'success': False,
                'error': '참가자 정보가 없습니다.'
            })
        
        stored_payment_hash = participant_data.get('payment_hash')
        if not stored_payment_hash or stored_payment_hash != payment_hash:
            return JsonResponse({
                'success': False,
                'error': '결제 정보가 일치하지 않습니다.'
            })
        
        # 🛡️ 이미 결제 완료된 주문이 있는지 확인 (취소 불가)
        existing_orders = LiveLectureOrder.objects.filter(
            payment_hash=payment_hash,
            paid_at__isnull=False  # 실제 결제 완료된 주문만 확인
        )
        if existing_orders.exists():
            order = existing_orders.first()
            logger.warning(f"이미 결제 완료된 주문의 취소 시도 - 주문: {order.order_number}")
            return JsonResponse({
                'success': False,
                'error': '이미 결제가 완료된 주문은 취소할 수 없습니다.',
                'redirect_url': f'/lecture/{store_id}/live/{live_lecture_id}/complete/{order.id}/'
            })
        
        # 결제 상태를 한 번 더 확인 (마지막 안전장치)
        try:
            blink_service = get_blink_service_for_store(store)
            if blink_service:
                result = blink_service.check_invoice_status(payment_hash)
                if result['success'] and result['status'] == 'paid':
                    # 실제로는 결제가 완료된 경우 - 즉시 주문 생성 후 리다이렉트
                    logger.warning(f"취소 시도 중 결제 완료 발견 - payment_hash: {payment_hash}")
                    
                    with transaction.atomic():
                        try:
                            order = LiveLectureOrder.objects.create(
                                live_lecture=live_lecture,
                                user=request.user,
                                price=participant_data['price'],
                                status='confirmed',
                                payment_hash=payment_hash,
                                payment_request=participant_data['payment_request'],
                                paid_at=timezone.now(),
                                confirmed_at=timezone.now(),
                                is_temporary_reserved=False
                            )
                        except Exception as create_error:
                            # 이미 주문이 존재하는 경우 기존 주문 사용
                            if 'unique_active_live_lecture_order_per_user' in str(create_error):
                                order = LiveLectureOrder.objects.filter(
                                    live_lecture=live_lecture,
                                    user=request.user,
                                    status__in=['confirmed', 'completed'],
                                    paid_at__isnull=False  # 실제 결제 완료된 주문만 확인
                                ).first()
                                if not order:
                                    raise create_error
                            else:
                                raise create_error
                    
                    # 세션에서 참가자 정보 삭제 (결제 완료되었으므로 삭제)
                    if f'live_lecture_participant_data_{live_lecture_id}' in request.session:
                        del request.session[f'live_lecture_participant_data_{live_lecture_id}']
                    
                    # 주최자에게 알림 이메일 발송
                    try:
                        from .services import send_live_lecture_notification_email
                        send_live_lecture_notification_email(order)
                    except Exception:
                        pass  # 이메일 발송 실패는 무시하고 진행
                    
                    return JsonResponse({
                        'success': False,
                        'error': '결제가 이미 완료되었습니다.',
                        'redirect_url': f'/lecture/{store_id}/live/{live_lecture_id}/complete/{order.id}/'
                    })
        except Exception as e:
            # 결제 상태 확인 실패는 무시하고 취소 계속 진행
            logger.warning(f"취소 시 결제 상태 확인 실패 (계속 진행): {e}")
        
        # 🔄 밋업과 동일: 세션에서 참가자 정보만 삭제 (DB에는 아무것도 저장하지 않음)
        if f'live_lecture_participant_data_{live_lecture_id}' in request.session:
            del request.session[f'live_lecture_participant_data_{live_lecture_id}']
            logger.debug(f"세션에서 참가자 정보 삭제 완료 - live_lecture_id: {live_lecture_id}")
        
        return JsonResponse({
            'success': True,
            'message': '결제가 취소되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"결제 취소 중 오류: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'결제 취소 중 오류가 발생했습니다: {str(e)}'
        }, status=500)

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
