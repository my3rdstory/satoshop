from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Category(models.Model):
    """강의 카테고리"""
    name = models.CharField(max_length=100, verbose_name="카테고리명")
    description = models.TextField(blank=True, verbose_name="설명")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    
    class Meta:
        verbose_name = "카테고리"
        verbose_name_plural = "카테고리"
        
    def __str__(self):
        return self.name


class Lecture(models.Model):
    """강의"""
    DIFFICULTY_CHOICES = [
        ('beginner', '초급'),
        ('intermediate', '중급'),
        ('advanced', '고급'),
    ]
    
    STATUS_CHOICES = [
        ('draft', '임시저장'),
        ('published', '게시됨'),
        ('closed', '마감'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="강의명")
    description = models.TextField(verbose_name="강의 설명")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="카테고리")
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="강사")
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, verbose_name="난이도")
    duration = models.PositiveIntegerField(verbose_name="강의 시간(분)")
    max_students = models.PositiveIntegerField(verbose_name="최대 수강인원")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="가격")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="상태")
    start_date = models.DateTimeField(verbose_name="강의 시작일")
    end_date = models.DateTimeField(verbose_name="강의 종료일")
    thumbnail = models.ImageField(upload_to='lectures/thumbnails/', blank=True, null=True, verbose_name="썸네일")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    class Meta:
        verbose_name = "강의"
        verbose_name_plural = "강의"
        ordering = ['-created_at']
        
    def __str__(self):
        return self.title
    
    @property
    def enrolled_count(self):
        """등록된 수강생 수"""
        return self.enrollments.filter(status='active').count()
    
    @property
    def is_full(self):
        """수강 인원 마감 여부"""
        return self.enrolled_count >= self.max_students
    
    @property
    def is_active(self):
        """강의 진행 중 여부"""
        now = timezone.now()
        return self.start_date <= now <= self.end_date


class LectureEnrollment(models.Model):
    """강의 수강 등록"""
    STATUS_CHOICES = [
        ('active', '수강중'),
        ('completed', '수강완료'),
        ('cancelled', '취소'),
    ]
    
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='enrollments', verbose_name="강의")
    student = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="수강생")
    enrolled_at = models.DateTimeField(auto_now_add=True, verbose_name="등록일")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="상태")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="수강완료일")
    
    class Meta:
        verbose_name = "강의 수강 등록"
        verbose_name_plural = "강의 수강 등록"
        unique_together = ['lecture', 'student']  # 한 강의에 같은 학생이 중복 등록 불가
        
    def __str__(self):
        return f"{self.student.username} - {self.lecture.title}"


class LectureReview(models.Model):
    """강의 리뷰"""
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='reviews', verbose_name="강의")
    student = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="수강생")
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)], verbose_name="평점")
    comment = models.TextField(verbose_name="리뷰 내용")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="작성일")
    
    class Meta:
        verbose_name = "강의 리뷰"
        verbose_name_plural = "강의 리뷰"
        unique_together = ['lecture', 'student']  # 한 강의에 한 학생당 하나의 리뷰만
        
    def __str__(self):
        return f"{self.lecture.title} - {self.rating}점"
