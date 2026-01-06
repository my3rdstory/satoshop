from django.conf import settings
from django.db import models


class Minihome(models.Model):
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="미니홈 접속 라우트 슬러그 (예: myhome)",
    )
    display_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="관리용 이름 (선택)",
    )
    owners = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="minihomes",
        help_text="미니홈 관리 권한을 가진 사용자",
        blank=True,
    )
    draft_sections = models.JSONField(
        default=list,
        blank=True,
        help_text="미리보기용 섹션 구성(JSON)",
    )
    published_sections = models.JSONField(
        default=list,
        blank=True,
        help_text="공개용 섹션 구성(JSON)",
    )
    is_published = models.BooleanField(
        default=False,
        help_text="공개 여부",
    )
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "미니홈"
        verbose_name_plural = "미니홈"

    def __str__(self) -> str:
        return self.display_name or self.slug
