from django import forms


ROLE_CHOICES = (
    ("client", "의뢰자"),
    ("performer", "수행자"),
)

PAYMENT_TYPE_CHOICES = (
    ("one_time", "일괄 지급"),
    ("milestone", "분할 지급"),
)

CHAT_MODE_CHOICES = (
    ("off", "채팅 끔"),
    ("on", "채팅 켬"),
)


class ContractDraftForm(forms.Form):
    """직접 계약 생성 1차 초안 폼."""

    title = forms.CharField(
        label="계약 제목",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "예: 디자인 컨설팅 계약"}),
    )
    role = forms.ChoiceField(
        label="나의 역할",
        choices=ROLE_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "role-radio"}),
    )
    start_date = forms.DateField(
        label="계약 시작일",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "input"}),
    )
    end_date = forms.DateField(
        label="계약 종료일",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "input"}),
    )
    amount_sats = forms.IntegerField(
        label="총 계약 금액 (사토시)",
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "input", "placeholder": "예: 250000"}),
    )
    payment_type = forms.ChoiceField(
        label="지불 조건",
        choices=PAYMENT_TYPE_CHOICES,
        widget=forms.RadioSelect(),
    )
    enable_chat = forms.ChoiceField(
        label="채팅 기능",
        choices=CHAT_MODE_CHOICES,
        widget=forms.HiddenInput(),
        initial="off",
    )
    email_recipient = forms.EmailField(
        label="계약서 수신 이메일 (선택)",
        required=False,
        widget=forms.EmailInput(attrs={"class": "input", "placeholder": "you@example.com"}),
    )
    work_log_markdown = forms.CharField(
        label="수행 내역 메모 (Markdown)",
        required=False,
        max_length=10000,
        widget=forms.Textarea(
            attrs={
                "class": "textarea worklog-textarea",
                "rows": 8,
                "placeholder": "최대 10,000자까지 작성 가능합니다. Markdown 형식을 사용할 수 있어요.",
            }
        ),
        help_text="최대 10,000자까지 입력 가능하며 Markdown을 지원합니다.",
    )
    attachment_manifest = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "id_attachment_manifest"}),
    )
    agree_privacy = forms.BooleanField(
        label="개인정보 수집 및 이용에 동의합니다.",
        required=True,
    )
    agree_confidentiality = forms.BooleanField(
        label="계약 내용 비밀 유지 및 시스템 책임 범위를 이해했습니다.",
        required=True,
    )
    agree_intermediary = forms.BooleanField(
        label="중계자인 본 시스템은 의뢰자와 수행자의 계약 이행에 관여하지 않으며, 계약 불이행에 대한 어떠한 책임도 지지 않음을 이해합니다.",
        required=True,
    )
