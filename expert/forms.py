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
        label="수행자 라이트닝 주소 (필수)",
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
    confirm_privacy = forms.BooleanField(
        label="개인정보 수집 및 이용에 동의합니다.",
        required=True,
        widget=forms.CheckboxInput(attrs={"data-signature-confirm": "true"}),
    )
    confirm_confidentiality = forms.BooleanField(
        label="계약 내용 비밀 유지 및 시스템 책임 범위를 이해했습니다.",
        required=True,
        widget=forms.CheckboxInput(attrs={"data-signature-confirm": "true"}),
    )
    confirm_system = forms.BooleanField(
        label="중계자인 본 시스템은 계약 이행에 관여하지 않으며, 불이행에 대한 책임이 없음을 이해합니다.",
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

    agree_reviewed = forms.BooleanField(
        label="계약 내용을 모두 확인했고, 자필 서명과 결제를 완료했습니다.",
        required=True,
        widget=forms.CheckboxInput(attrs={"data-signature-confirm": "true"}),
    )


class ContractIntegrityCheckForm(forms.Form):
    """계약 위변조 검증 입력 폼."""

    document_slug = forms.ChoiceField(
        label="검증할 계약",
        choices=(),
        widget=forms.Select(attrs={"class": "select is-fullwidth"}),
    )
    pdf_file = forms.FileField(
        label="검증 대상 PDF",
        widget=forms.FileInput(attrs={"class": "file-input", "accept": ".pdf"}),
        help_text="서버에서 받은 최종 계약서 PDF를 업로드해 위변조 여부를 확인합니다.",
    )

    def __init__(self, *args, documents=None, **kwargs):
        self.documents = documents or []
        super().__init__(*args, **kwargs)
        self._document_map = {doc.slug: doc for doc in self.documents}
        choices = [
            ("", "계약을 선택하세요"),
            *[(doc.slug, doc.payload.get("title", doc.slug)) for doc in self.documents],
        ]
        self.fields["document_slug"].choices = choices

    def clean_document_slug(self):
        slug = self.cleaned_data.get("document_slug")
        if not slug:
            raise forms.ValidationError("계약을 선택해 주세요.")
        if slug not in self._document_map:
            raise forms.ValidationError("선택한 계약을 조회할 수 없습니다.")
        return slug

    def clean_pdf_file(self):
        uploaded = self.cleaned_data.get("pdf_file")
        if not uploaded:
            raise forms.ValidationError("검증할 PDF를 업로드해 주세요.")
        content_type = (uploaded.content_type or "").lower()
        if content_type and "pdf" not in content_type:
            raise forms.ValidationError("PDF 파일만 업로드할 수 있습니다.")
        return uploaded

    def get_document(self):
        slug = self.cleaned_data.get("document_slug")
        return self._document_map.get(slug)
    email = forms.EmailField(
        label="이메일 (선택)",
        widget=forms.EmailInput(attrs={"class": "input", "placeholder": "you@example.com"}),
    )
    performer_lightning_address = forms.CharField(
        label="정산 라이트닝 주소 (필수)",
        required=False,
        max_length=120,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "placeholder": "예: performer@ln.example",
            }
        ),
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
        label="중계자인 본 시스템은 계약 이행에 관여하지 않으며, 불이행에 대한 책임이 없음을 이해합니다.",
        required=True,
        widget=forms.CheckboxInput(attrs={"data-signature-confirm": "true"}),
    )

    def __init__(self, *args, require_performer_lightning=False, **kwargs):
        self.require_performer_lightning = require_performer_lightning
        super().__init__(*args, **kwargs)
        if not self.require_performer_lightning:
            self.fields.pop("performer_lightning_address", None)
        else:
            self.fields["performer_lightning_address"].required = True

    def clean_signature_data(self):
        data = self.cleaned_data["signature_data"]
        if not data or not data.startswith("data:image/"):
            raise forms.ValidationError("자필 서명을 캡처해 주세요.")
        try:
            base64.b64decode(data.split(",")[1])
        except Exception as exc:  # pylint: disable=broad-except
            raise forms.ValidationError("서명 데이터가 올바르지 않습니다.") from exc
        return data
