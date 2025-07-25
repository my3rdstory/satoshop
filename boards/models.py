from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone


class Notice(models.Model):
    """공지사항 게시글 모델"""
    sequence_number = models.PositiveIntegerField('순서번호', unique=True, null=True, blank=True)
    title = models.CharField('제목', max_length=200)
    content = models.TextField('내용')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='작성자')
    created_at = models.DateTimeField('작성일', default=timezone.now)
    updated_at = models.DateTimeField('수정일', auto_now=True)
    views = models.PositiveIntegerField('조회수', default=0)
    is_pinned = models.BooleanField('공지 고정', default=False)
    is_active = models.BooleanField('활성화', default=True)

    class Meta:
        verbose_name = '공지사항'
        verbose_name_plural = '공지사항'
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['is_active', '-created_at']),
            models.Index(fields=['is_pinned', '-created_at']),
            models.Index(fields=['sequence_number']),
            models.Index(fields=['author']),
            models.Index(fields=['views']),
            models.Index(fields=['is_active', 'is_pinned', 'created_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('boards:notice_detail', kwargs={'pk': self.pk})

    def increase_views(self):
        """조회수 증가"""
        self.views += 1
        self.save(update_fields=['views'])

    def save(self, *args, **kwargs):
        """저장 시 순서 번호 자동 할당"""
        if not self.sequence_number:
            # 가장 큰 순서 번호를 찾아서 +1
            last_notice = Notice.objects.filter(sequence_number__isnull=False).order_by('-sequence_number').first()
            if last_notice:
                self.sequence_number = last_notice.sequence_number + 1
            else:
                self.sequence_number = 1
        super().save(*args, **kwargs)


class NoticeComment(models.Model):
    """공지사항 댓글 모델"""
    notice = models.ForeignKey(Notice, on_delete=models.CASCADE, related_name='comments', verbose_name='공지사항')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='작성자')
    content = models.TextField('댓글 내용')
    created_at = models.DateTimeField('작성일', default=timezone.now)
    updated_at = models.DateTimeField('수정일', auto_now=True)
    is_active = models.BooleanField('활성화', default=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                              related_name='replies', verbose_name='부모 댓글')

    class Meta:
        verbose_name = '공지사항 댓글'
        verbose_name_plural = '공지사항 댓글'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['notice', 'is_active', '-created_at']),
        ]

    def __str__(self):
        return f'{self.notice.title} - {self.author.username}'

    @property
    def is_reply(self):
        """대댓글인지 확인"""
        return self.parent is not None
