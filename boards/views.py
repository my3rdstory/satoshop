from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import Notice, NoticeComment
import json


def is_staff_or_superuser(user):
    """스태프 또는 슈퍼유저인지 확인"""
    return user.is_staff or user.is_superuser


class NoticeListView(LoginRequiredMixin, ListView):
    """공지사항 목록 뷰"""
    model = Notice
    template_name = 'boards/notice/list.html'
    context_object_name = 'notices'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Notice.objects.filter(is_active=True)
        
        # 검색 기능
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(content__icontains=search)
            )
        
        return queryset.order_by('-is_pinned', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['can_create'] = is_staff_or_superuser(self.request.user)
        return context


class NoticeDetailView(LoginRequiredMixin, DetailView):
    """공지사항 상세 뷰"""
    model = Notice
    template_name = 'boards/notice/detail.html'
    context_object_name = 'notice'
    
    def get_object(self):
        obj = get_object_or_404(Notice, pk=self.kwargs['pk'], is_active=True)
        # 조회수 증가
        obj.increase_views()
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        notice = self.get_object()
        
        # 댓글 목록 (대댓글 제외한 최상위 댓글만)
        comments = NoticeComment.objects.filter(
            notice=notice, 
            is_active=True, 
            parent=None
        ).select_related('author').prefetch_related('replies__author')
        
        context['comments'] = comments
        context['can_edit'] = (
            self.request.user == notice.author or 
            is_staff_or_superuser(self.request.user)
        )
        context['can_create'] = is_staff_or_superuser(self.request.user)
        return context


@login_required
@user_passes_test(is_staff_or_superuser)
def notice_create(request):
    """공지사항 작성"""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        is_pinned = request.POST.get('is_pinned') == 'on'
        
        if not title or not content:
            messages.error(request, '제목과 내용을 모두 입력해주세요.')
            return render(request, 'boards/notice/create.html', {
                'title': title,
                'content': content,
                'is_pinned': is_pinned
            })
        
        notice = Notice.objects.create(
            title=title,
            content=content,
            author=request.user,
            is_pinned=is_pinned
        )
        
        messages.success(request, '공지사항이 성공적으로 작성되었습니다.')
        return redirect('boards:notice_detail', pk=notice.pk)
    
    return render(request, 'boards/notice/create.html')


@login_required
@user_passes_test(is_staff_or_superuser)
def notice_edit(request, pk):
    """공지사항 수정"""
    notice = get_object_or_404(Notice, pk=pk, is_active=True)
    
    # 작성자이거나 관리자만 수정 가능
    if not (request.user == notice.author or is_staff_or_superuser(request.user)):
        messages.error(request, '수정 권한이 없습니다.')
        return redirect('boards:notice_detail', pk=pk)
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        is_pinned = request.POST.get('is_pinned') == 'on'
        
        if not title or not content:
            messages.error(request, '제목과 내용을 모두 입력해주세요.')
            return render(request, 'boards/notice/edit.html', {
                'notice': notice,
                'title': title,
                'content': content,
                'is_pinned': is_pinned
            })
        
        notice.title = title
        notice.content = content
        notice.is_pinned = is_pinned
        notice.save()
        
        messages.success(request, '공지사항이 성공적으로 수정되었습니다.')
        return redirect('boards:notice_detail', pk=notice.pk)
    
    return render(request, 'boards/notice/edit.html', {'notice': notice})


@login_required
@user_passes_test(is_staff_or_superuser)
def notice_delete(request, pk):
    """공지사항 삭제 (비활성화)"""
    notice = get_object_or_404(Notice, pk=pk, is_active=True)
    
    # 작성자이거나 관리자만 삭제 가능
    if not (request.user == notice.author or is_staff_or_superuser(request.user)):
        messages.error(request, '삭제 권한이 없습니다.')
        return redirect('boards:notice_detail', pk=pk)
    
    if request.method == 'POST':
        notice.is_active = False
        notice.save()
        messages.success(request, '공지사항이 삭제되었습니다.')
        return redirect('boards:notice_list')
    
    return render(request, 'boards/notice/delete.html', {'notice': notice})


@login_required
@require_POST
def comment_create(request, notice_pk):
    """댓글 작성"""
    notice = get_object_or_404(Notice, pk=notice_pk, is_active=True)
    content = request.POST.get('content', '').strip()
    parent_id = request.POST.get('parent_id')
    
    if not content:
        messages.error(request, '댓글 내용을 입력해주세요.')
        return redirect('boards:notice_detail', pk=notice_pk)
    
    # 부모 댓글 확인 (대댓글인 경우)
    parent = None
    if parent_id:
        parent = get_object_or_404(NoticeComment, pk=parent_id, is_active=True)
    
    comment = NoticeComment.objects.create(
        notice=notice,
        author=request.user,
        content=content,
        parent=parent
    )
    
    messages.success(request, '댓글이 성공적으로 작성되었습니다.')
    return redirect('boards:notice_detail', pk=notice_pk)


@login_required
def comment_edit(request, comment_pk):
    """댓글 수정"""
    comment = get_object_or_404(NoticeComment, pk=comment_pk, is_active=True)
    
    # 작성자만 수정 가능
    if request.user != comment.author:
        messages.error(request, '댓글 수정 권한이 없습니다.')
        return redirect('boards:notice_detail', pk=comment.notice.pk)
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        
        if not content:
            messages.error(request, '댓글 내용을 입력해주세요.')
            return redirect('boards:notice_detail', pk=comment.notice.pk)
        
        comment.content = content
        comment.save()
        
        messages.success(request, '댓글이 수정되었습니다.')
        return redirect('boards:notice_detail', pk=comment.notice.pk)
    
    return render(request, 'boards/notice/comment_edit.html', {'comment': comment})


@login_required
@require_POST
def comment_delete(request, comment_pk):
    """댓글 삭제 (비활성화)"""
    comment = get_object_or_404(NoticeComment, pk=comment_pk, is_active=True)
    
    # 작성자이거나 관리자만 삭제 가능
    if not (request.user == comment.author or is_staff_or_superuser(request.user)):
        messages.error(request, '댓글 삭제 권한이 없습니다.')
        return redirect('boards:notice_detail', pk=comment.notice.pk)
    
    comment.is_active = False
    comment.save()
    
    messages.success(request, '댓글이 삭제되었습니다.')
    return redirect('boards:notice_detail', pk=comment.notice.pk)
