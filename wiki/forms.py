from __future__ import annotations

from django import forms
from django.core.validators import MaxLengthValidator

from .models import WikiEntry

TAG_LIMIT = 100


class WikiEntryForm(forms.ModelForm):
    """
    Backoffice form for managing wiki entries.
    """

    tags_input = forms.CharField(
        label="태그",
        required=False,
        help_text="콤마(,)로 구분해 최대 100개의 태그를 입력하세요.",
        widget=forms.TextInput(attrs={"placeholder": "예: 결제, 배송, 라이트닝"}),
    )

    class Meta:
        model = WikiEntry
        fields = ["title", "content", "is_published"]
        labels = {
            "title": "제목",
            "content": "내용",
            "is_published": "공개 여부",
        }
        widgets = {
            "title": forms.TextInput(attrs={"maxlength": 100}),
            "content": forms.Textarea(
                attrs={
                    "rows": 10,
                    "maxlength": 1000,
                }
            ),
        }
        help_texts = {
            "title": "제목은 100자 이내로 입력하세요.",
            "content": "내용은 1000자 이내로 입력하세요.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["tags_input"].initial = ", ".join(self.instance.tags)
        self.fields["content"].validators.append(MaxLengthValidator(1000))

    def clean_tags_input(self) -> list[str]:
        raw_value = self.cleaned_data.get("tags_input", "")
        if not raw_value:
            return []

        tags = [tag.strip() for tag in raw_value.split(",") if tag.strip()]
        unique_tags = []
        for tag in tags:
            if tag not in unique_tags:
                unique_tags.append(tag)

        if len(unique_tags) > TAG_LIMIT:
            raise forms.ValidationError(f"태그는 최대 {TAG_LIMIT}개까지 입력할 수 있습니다.")

        return unique_tags

    def save(self, commit: bool = True):
        tags = self.cleaned_data.pop("tags_input", [])
        instance = super().save(commit=False)
        instance.tags = tags
        if commit:
            instance.save()
        return instance
