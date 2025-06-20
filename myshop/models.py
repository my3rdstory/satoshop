from django.db import models
from django.core.exceptions import ValidationError
import re
from django.utils import timezone


def get_current_year_copyright():
    """현재 연도로 기본 저작권 문구 생성"""
    current_year = timezone.now().year
    return f"© {current_year} SatoShop. All rights reserved."

# Create your models here.

class ExchangeRate(models.Model):
    """업비트 BTC/KRW 환율 데이터"""
    
    btc_krw_rate = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        verbose_name="BTC/KRW 환율",
        help_text="1 BTC = ? KRW"
    )
    
    api_response_data = models.JSONField(
        verbose_name="API 응답 데이터",
        help_text="업비트 API 전체 응답 데이터"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="생성일",
        db_index=True
    )
    
    class Meta:
        verbose_name = "환율 데이터"
        verbose_name_plural = "환율 데이터"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"1 BTC = {self.btc_krw_rate:,} KRW ({self.created_at.strftime('%Y-%m-%d %H:%M:%S')})"
    
    @classmethod
    def get_latest_rate(cls):
        """최신 환율 데이터 가져오기"""
        return cls.objects.first()
    
    @classmethod
    def cleanup_old_rates(cls, keep_count=10):
        """오래된 환율 데이터 정리 (최근 10개만 유지)"""
        if cls.objects.count() > keep_count:
            old_rates = cls.objects.all()[keep_count:]
            cls.objects.filter(id__in=[rate.id for rate in old_rates]).delete()
    
    def get_sats_from_krw(self, krw_amount):
        """원화 금액을 사토시로 변환"""
        if not krw_amount or krw_amount <= 0:
            return 0
        
        # 1 BTC = 100,000,000 사토시
        btc_amount = krw_amount / float(self.btc_krw_rate)
        sats_amount = btc_amount * 100_000_000
        return int(sats_amount)
    
    def get_krw_from_sats(self, sats_amount):
        """사토시를 원화 금액으로 변환"""
        if not sats_amount or sats_amount <= 0:
            return 0
        
        # 1 BTC = 100,000,000 사토시
        btc_amount = sats_amount / 100_000_000
        krw_amount = btc_amount * float(self.btc_krw_rate)
        return int(krw_amount)

class SiteSettings(models.Model):
    """사이트 전역 설정"""
    
    # 기본 설정
    site_title = models.CharField(
        max_length=100, 
        default="SatoShop", 
        verbose_name="사이트 제목",
        help_text="브라우저 탭에 표시되는 사이트 제목"
    )
    
    site_description = models.CharField(
        max_length=200,
        default="비트코인 라이트닝 결제 플랫폼", 
        verbose_name="사이트 설명",
        help_text="메타 태그에 사용되는 사이트 설명 (최대 200자)"
    )
    
    # SEO 메타 태그
    meta_keywords = models.TextField(
        blank=True,
        verbose_name="메타 키워드",
        help_text="SEO용 메타 키워드 (쉼표로 구분, 예: 비트코인, 라이트닝, 온라인스토어, 암호화폐)"
    )
    
    admin_site_header = models.CharField(
        max_length=100,
        default="SatoShop 관리자",
        verbose_name="관리자 사이트 제목",
        help_text="Django 관리자 페이지 상단에 표시되는 제목"
    )
    
    site_logo_url = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="사이트 로고 이미지 경로",
        help_text="메인 사이트에 표시될 로고 이미지 경로 (예: /static/images/logo.png 또는 https://example.com/logo.png). 비어있으면 'SatoShop' 텍스트로 표시됩니다."
    )
    
    # 홈페이지 히어로 섹션
    hero_title = models.CharField(
        max_length=200, 
        default="누구나 쉽게 만드는 비트코인 온라인 스토어", 
        verbose_name="히어로 제목"
    )
    
    hero_subtitle = models.TextField(
        default="복잡한 설정 없이 5분만에 온라인 스토어를 만들고 비트코인으로 결제받으세요", 
        verbose_name="히어로 부제목"
    )
    
    hero_description = models.TextField(
        default="코딩 없이 5분 만에 스토어 구축 • 즉석 비트코인 결제 • 전세계 고객 접근",
        verbose_name="히어로 설명",
        help_text="히어로 섹션 하단에 표시될 추가 설명"
    )
    
    hero_primary_button_text = models.CharField(
        max_length=50,
        default="지금 시작하기",
        verbose_name="주요 버튼 텍스트",
        help_text="히어로 섹션의 주요 액션 버튼 텍스트"
    )
    
    hero_secondary_button_text = models.CharField(
        max_length=50,
        default="스토어 둘러보기",
        verbose_name="보조 버튼 텍스트", 
        help_text="히어로 섹션의 보조 액션 버튼 텍스트"
    )
    
    # 유튜브 비디오 설정
    youtube_video_id = models.CharField(
        max_length=20, 
        default="dd2RzyPu4ok", 
        verbose_name="유튜브 비디오 ID",
        help_text="유튜브 URL에서 v= 뒤의 ID만 입력하세요 (예: dd2RzyPu4ok)"
    )
    
    youtube_autoplay = models.BooleanField(
        default=True, 
        verbose_name="자동 재생",
        help_text="페이지 로드 시 비디오 자동 재생"
    )
    
    youtube_mute = models.BooleanField(
        default=True, 
        verbose_name="음소거",
        help_text="비디오 음소거 상태로 재생"
    )
    
    youtube_loop = models.BooleanField(
        default=True, 
        verbose_name="반복 재생",
        help_text="비디오 반복 재생"
    )
    
    youtube_controls = models.BooleanField(
        default=False, 
        verbose_name="컨트롤 표시",
        help_text="비디오 재생 컨트롤 표시"
    )
    
    # 연락처 정보
    contact_email = models.EmailField(
        blank=True, 
        verbose_name="연락처 이메일",
        help_text="고객 문의용 이메일 주소"
    )
    
    # 소셜 미디어
    github_url = models.URLField(
        blank=True, 
        verbose_name="GitHub URL",
        help_text="GitHub 프로젝트 링크"
    )
    
    # 푸터 설정
    footer_company_name = models.CharField(
        max_length=100,
        default="SatoShop",
        verbose_name="회사명/서비스명",
        help_text="푸터에 표시될 회사명 또는 서비스명"
    )
    
    footer_description = models.TextField(
        default="비트코인 라이트닝으로 누구나 쉽게 사용하는 온라인 스토어 플랫폼",
        verbose_name="푸터 설명",
        help_text="푸터에 표시될 간단한 서비스 설명"
    )
    
    footer_copyright = models.CharField(
        max_length=200,
        default=get_current_year_copyright,
        verbose_name="저작권 표시",
        help_text="푸터 하단에 표시될 저작권 문구 (자동으로 현재 연도가 설정됩니다)"
    )
    
    footer_address = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="주소",
        help_text="회사 주소 (선택사항)"
    )
    
    footer_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="전화번호",
        help_text="고객 문의 전화번호 (선택사항)"
    )
    
    footer_business_hours = models.CharField(
        max_length=100,
        default="24시간 온라인 서비스",
        verbose_name="운영시간",
        help_text="서비스 운영시간 안내"
    )
    
    # 소셜 미디어 링크 (기존 github_url 확장)
    footer_twitter_url = models.URLField(
        blank=True,
        verbose_name="트위터 URL",
        help_text="트위터 프로필 링크"
    )
    
    footer_telegram_url = models.URLField(
        blank=True,
        verbose_name="텔레그램 URL", 
        help_text="텔레그램 채널/그룹 링크"
    )
    
    footer_discord_url = models.URLField(
        blank=True,
        verbose_name="디스코드 URL",
        help_text="디스코드 서버 링크"
    )
    
    # 기능 활성화/비활성화
    enable_user_registration = models.BooleanField(
        default=True, 
        verbose_name="회원가입 허용",
        help_text="새로운 사용자 회원가입 허용"
    )
    
    enable_store_creation = models.BooleanField(
        default=True, 
        verbose_name="스토어 생성 허용",
        help_text="사용자의 새 스토어 생성 허용"
    )
    
    # Google Analytics 설정
    google_analytics_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Google Analytics ID",
        help_text="Google Analytics 추적 ID (예: G-XXXXXXXXXX 또는 UA-XXXXXXXXX-X)"
    )
    
    # Open Graph 설정
    og_default_image = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="기본 Open Graph 이미지",
        help_text="링크 공유 시 표시될 기본 이미지 경로 (1200x630 권장, 예: /static/images/og-image.png 또는 https://example.com/image.png)"
    )
    
    og_site_name = models.CharField(
        max_length=100,
        default="SatoShop",
        verbose_name="Open Graph 사이트명",
        help_text="소셜 미디어에서 표시될 사이트명"
    )
    
    # 파비콘 설정
    favicon_url = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="파비콘 경로",
        help_text="사이트 파비콘 이미지 경로 (16x16, 32x32 권장, PNG 형식, 예: /static/images/favicon.png 또는 https://example.com/favicon.png)"
    )
    
    # 블링크 API 설정
    blink_api_doc_url = models.URLField(
        default="#",
        verbose_name="블링크 API 문서 링크",
        help_text="스토어 생성 시 블링크 API 정보 얻는 방법 문서 링크"
    )
    
    # 메타 정보
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    class Meta:
        verbose_name = "사이트 설정"
        verbose_name_plural = "사이트 설정"
        # 성능 최적화를 위한 인덱스 추가
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
            models.Index(fields=['enable_user_registration']),  # 기능 설정 조회용
            models.Index(fields=['enable_store_creation']),     # 기능 설정 조회용
        ]
    
    def clean(self):
        """유튜브 비디오 ID 유효성 검사"""
        if self.youtube_video_id:
            # 유튜브 비디오 ID 패턴 검사 (11자리 영숫자, 하이픈, 언더스코어)
            pattern = r'^[a-zA-Z0-9_-]{11}$'
            if not re.match(pattern, self.youtube_video_id):
                raise ValidationError({
                    'youtube_video_id': '올바른 유튜브 비디오 ID를 입력하세요. (11자리 영숫자, 하이픈, 언더스코어만 허용)'
                })
    
    def save(self, *args, **kwargs):
        # 싱글톤 패턴: 하나의 설정만 존재하도록
        if not self.pk and SiteSettings.objects.exists():
            # 기존 설정이 있으면 업데이트
            existing = SiteSettings.objects.first()
            self.pk = existing.pk
        
        # 저작권 표시가 비어있거나 © 기호가 없으면 기본값으로 설정
        if not self.footer_copyright or not self.footer_copyright.startswith('©'):
            self.footer_copyright = get_current_year_copyright()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"사이트 설정 ({self.updated_at.strftime('%Y-%m-%d %H:%M')})"
    
    @classmethod
    def get_settings(cls):
        """현재 사이트 설정 가져오기"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
    

    
    def get_youtube_embed_url(self):
        """유튜브 임베드 URL 생성 (UI 요소 최대한 숨김)"""
        if not self.youtube_video_id:
            return ""
        
        params = []
        if self.youtube_autoplay:
            params.append("autoplay=1")
        if self.youtube_mute:
            params.append("mute=1")
        if self.youtube_loop:
            params.append(f"loop=1&playlist={self.youtube_video_id}")
        if not self.youtube_controls:
            params.append("controls=0")
        
        # UI 요소 숨김을 위한 강화된 매개변수
        params.extend([
            "showinfo=0",           # 비디오 정보 숨김
            "rel=0",                # 관련 동영상 숨김
            "iv_load_policy=3",     # 주석 숨김
            "modestbranding=1",     # 유튜브 로고 최소화
            "disablekb=1",          # 키보드 컨트롤 비활성화
            "fs=0",                 # 전체화면 버튼 숨김
            "cc_load_policy=0",     # 자막 비활성화
            "playsinline=1",        # 인라인 재생
            "enablejsapi=1",        # JavaScript API 활성화
            "origin=" + "localhost", # 도메인 제한 (보안)
            "widget_referrer=" + "localhost",  # 참조자 설정
            "start=0",              # 시작 시간
            "end=999999",           # 종료 시간 (매우 긴 시간)
            "color=white",          # 진행바 색상
            "hl=ko",                # 언어 설정
            "cc_lang_pref=ko",      # 자막 언어
            "vq=hd1080"             # 비디오 품질
        ])
        
        param_string = "&".join(params)
        return f"https://www.youtube.com/embed/{self.youtube_video_id}?{param_string}"

class DocumentContent(models.Model):
    """사이트 문서 관리 (이용약관, 개인정보처리방침, 환불정책 등)"""
    
    DOCUMENT_TYPES = [
        ('terms', '이용약관'),
        ('privacy', '개인정보처리방침'),
        ('refund', '환불 및 반품 정책'),
    ]
    
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPES,
        unique=True,
        verbose_name="문서 유형",
        help_text="관리할 문서의 유형을 선택하세요"
    )
    
    title = models.CharField(
        max_length=100,
        verbose_name="문서 제목",
        help_text="사이트에 표시될 문서 제목"
    )
    
    content = models.TextField(
        verbose_name="문서 내용",
        help_text="마크다운 형식으로 작성하세요. HTML 태그도 사용 가능합니다."
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="활성화",
        help_text="체크 해제 시 사이트에서 숨겨집니다"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    class Meta:
        verbose_name = "문서 관리"
        verbose_name_plural = "문서 관리"
        ordering = ['document_type']
        indexes = [
            models.Index(fields=['document_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.get_document_type_display()}"
    
    @classmethod
    def get_active_documents(cls):
        """활성화된 문서들을 가져오기"""
        return cls.objects.filter(is_active=True)
    
    @classmethod
    def get_document(cls, document_type):
        """특정 유형의 문서 가져오기"""
        try:
            return cls.objects.get(document_type=document_type, is_active=True)
        except cls.DoesNotExist:
            return None
    
    def get_rendered_content(self):
        """마크다운을 HTML로 변환 (기존의 마크다운 렌더링 기능 활용)"""
        if not self.content:
            return ''
        
        # 기존의 마크다운 렌더링 로직 사용 (products.templatetags.product_extras와 동일)
        import markdown
        from markdown.extensions import codehilite, fenced_code, tables
        
        # Markdown 확장 기능 설정
        extensions = [
            'markdown.extensions.fenced_code',
            'markdown.extensions.tables',
            'markdown.extensions.nl2br',
            'markdown.extensions.codehilite',
            'markdown.extensions.sane_lists',
        ]
        
        extension_configs = {
            'markdown.extensions.codehilite': {
                'css_class': 'highlight',
                'use_pygments': False,  # 간단한 코드 하이라이팅
            }
        }
        
        # Markdown을 HTML로 변환
        md = markdown.Markdown(
            extensions=extensions,
            extension_configs=extension_configs,
            safe_mode=False
        )
        
        html = md.convert(self.content)
        
        # 기본적인 링크에 target="_blank" 추가
        import re
        html = re.sub(
            r'<a\s+([^>]*href="https?://[^"]*"[^>]*)>',
            r'<a \1 target="_blank" rel="noopener noreferrer">',
            html
        )
        
        return html
