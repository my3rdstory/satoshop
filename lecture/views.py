from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Avg
from django.utils import timezone
from .models import Lecture, Category, LectureEnrollment, LectureReview


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
