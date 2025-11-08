import base64
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
    one_time_due_date = forms.DateField(
        label="일괄 지급 예정일",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "input"}),
    )
    one_time_condition = forms.CharField(
        label="일괄 지급 조건",
        required=False,
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "예: 검수 완료 후 3일 내"}),
        max_length=200,
    )
    enable_chat = forms.ChoiceField(
        label="채팅 기능",
        choices=CHAT_MODE_CHOICES,
        widget=forms.HiddenInput(),
        initial="off",
    )
    client_lightning_address = forms.CharField(
        label="의뢰자 라이트닝 주소",
        required=False,
        max_length=120,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": "예: client@ln.example",
            }
        ),
    )
    performer_lightning_address = forms.CharField(
        label="수행자 라이트닝 주소",
        required=False,
        max_length=120,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": "예: performer@ln.example",
            }
        ),
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

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        performer_lightning = cleaned_data.get("performer_lightning_address")
        if role == "performer" and not performer_lightning:
            self.add_error(
                "performer_lightning_address",
                "수행자는 라이트닝 주소를 반드시 입력해야 합니다.",
            )
        return cleaned_data


class ContractReviewForm(forms.Form):
    """계약 생성자가 최종 검토 단계에서 사용하는 폼."""

    signature_data = forms.CharField(widget=forms.HiddenInput(attrs={"data-signature-input": "true"}))
    confirm_reviewed = forms.BooleanField(
        label="계약서 내용을 모두 확인했으며 자필 서명했습니다.",
        required=True,
        widget=forms.CheckboxInput(attrs={"data-signature-confirm": "true"}),
    )

    def clean_signature_data(self):
        data = self.cleaned_data["signature_data"]
        if not data or not data.startswith("data:image/"):
            raise forms.ValidationError("자필 서명을 캡처해 주세요.")
        try:
            base64.b64decode(data.split(",")[1])
        except Exception as exc:  # pylint: disable=broad-except
            raise forms.ValidationError("서명 데이터가 올바르지 않습니다.") from exc
        return data


class CounterpartySignatureForm(forms.Form):
    """공유 주소에서 상대방이 사용하는 서명 폼."""

    email = forms.EmailField(
        label="이메일",
        widget=forms.EmailInput(attrs={"class": "input", "placeholder": "you@example.com"}),
    )
    signature_data = forms.CharField(widget=forms.HiddenInput(attrs={"data-signature-input": "true"}))
    agree_privacy = forms.BooleanField(
        label="개인정보 수집 및 이용에 동의합니다.",
        required=True,
        widget=forms.CheckboxInput(attrs={"data-signature-confirm": "true"}),
    )
    agree_confidentiality = forms.BooleanField(
        label="계약 내용 비밀 유지 조항을 이해했습니다.",
        required=True,
        widget=forms.CheckboxInput(attrs={"data-signature-confirm": "true"}),
    )
    agree_system = forms.BooleanField(
        label="중계 시스템 안내 사항을 모두 확인했습니다.",
        required=True,
        widget=forms.CheckboxInput(attrs={"data-signature-confirm": "true"}),
    )

    def clean_signature_data(self):
        data = self.cleaned_data["signature_data"]
        if not data or not data.startswith("data:image/"):
            raise forms.ValidationError("자필 서명을 캡처해 주세요.")
        try:
            base64.b64decode(data.split(",")[1])
        except Exception as exc:  # pylint: disable=broad-except
            raise forms.ValidationError("서명 데이터가 올바르지 않습니다.") from exc
        return data
