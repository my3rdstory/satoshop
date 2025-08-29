from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.db.models import F


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


class MemeTag(models.Model):
    """밈 태그 모델"""
    name = models.CharField('태그명', max_length=50, unique=True, db_index=True)
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    
    class Meta:
        verbose_name = '밈 태그'
        verbose_name_plural = '밈 태그'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.name


class MemePost(models.Model):
    """밈 게시글 모델"""
    title = models.CharField('제목', max_length=200)
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='작성자')
    image_path = models.CharField('이미지 경로', max_length=500)
    image_url = models.URLField('이미지 URL', max_length=500)
    thumbnail_path = models.CharField('썸네일 경로', max_length=500)
    thumbnail_url = models.URLField('썸네일 URL', max_length=500)
    original_filename = models.CharField('원본 파일명', max_length=255)
    file_size = models.PositiveIntegerField('파일 크기', default=0)
    width = models.PositiveIntegerField('이미지 너비', default=0)
    height = models.PositiveIntegerField('이미지 높이', default=0)
    tags = models.ManyToManyField(MemeTag, related_name='memes', verbose_name='태그', blank=True)
    views = models.PositiveIntegerField('조회수', default=0, db_index=True)
    list_copy_count = models.PositiveIntegerField('목록 복사 횟수', default=0)
    list_view_count = models.PositiveIntegerField('목록 보기 횟수', default=0)
    detail_copy_count = models.PositiveIntegerField('상세 복사 횟수', default=0)
    created_at = models.DateTimeField('작성일', default=timezone.now)
    updated_at = models.DateTimeField('수정일', auto_now=True)
    is_active = models.BooleanField('활성화', default=True)
    
    class Meta:
        verbose_name = '밈 게시글'
        verbose_name_plural = '밈 게시글'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', '-created_at']),  # 리스트 조회시 사용
            models.Index(fields=['author', 'is_active']),  # 특정 사용자의 활성 게시물 조회
            models.Index(fields=['views']),  # 조회수 순 정렬시 사용
            models.Index(fields=['created_at']),  # 날짜별 조회
            models.Index(fields=['updated_at']),  # 최근 수정된 게시물 조회
            models.Index(fields=['title']),  # 제목 검색시 사용
            models.Index(fields=['list_copy_count', 'list_view_count', 'detail_copy_count']),  # 통계 정렬/필터링
        ]
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('boards:meme_detail', kwargs={'pk': self.pk})
    
    def increase_views(self):
        """조회수 증가 - F() 표현식으로 경쟁 상태 방지"""
        # 클래스 메서드를 사용하여 self를 참조하지 않고 업데이트
        MemePost.objects.filter(pk=self.pk).update(views=F('views') + 1)
        self.refresh_from_db(fields=['views'])


class HallOfFame(models.Model):
    """Hall of Fame 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='사용자')
    title = models.CharField('제목', max_length=200)
    description = models.TextField('설명', blank=True)
    image_path = models.CharField('이미지 경로', max_length=500)
    image_url = models.URLField('이미지 URL', max_length=500)
    thumbnail_path = models.CharField('썸네일 경로', max_length=500)
    thumbnail_url = models.URLField('썸네일 URL', max_length=500)
    original_filename = models.CharField('원본 파일명', max_length=255)
    file_size = models.PositiveIntegerField('파일 크기', default=0)
    width = models.PositiveIntegerField('이미지 너비', default=0)
    height = models.PositiveIntegerField('이미지 높이', default=0)
    views = models.PositiveIntegerField('조회수', default=0, db_index=True)
    created_at = models.DateTimeField('작성일', default=timezone.now)
    updated_at = models.DateTimeField('수정일', auto_now=True)
    is_active = models.BooleanField('활성화', default=True)
    order = models.PositiveIntegerField('순서', default=0, db_index=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='created_hall_of_fame', verbose_name='등록자')
    
    class Meta:
        verbose_name = 'Hall of Fame'
        verbose_name_plural = 'Hall of Fame'
        ordering = ['order', '-created_at']
        indexes = [
            models.Index(fields=['is_active', 'order', '-created_at']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['order']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def get_absolute_url(self):
        return reverse('boards:hall_of_fame_list')
