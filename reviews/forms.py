from django import forms

from .models import Review


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiFileField(forms.FileField):
    """FileField that accepts multiple files and returns a list of uploads."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('required', False)
        kwargs.setdefault('widget', MultiFileInput(attrs={'multiple': True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):  # pylint: disable=signature-differs
        if not data:
            if self.required and not initial:
                raise forms.ValidationError(self.error_messages['required'], code='required')
            return []

        if not isinstance(data, (list, tuple)):
            data = [data]

        cleaned_files = []
        errors = []

        for uploaded in data:
            try:
                cleaned_files.append(super().clean(uploaded, initial))
            except forms.ValidationError as exc:
                errors.extend(exc.error_list)

        if errors:
            raise forms.ValidationError(errors)

        return cleaned_files


class ReviewForm(forms.ModelForm):
    images = MultiFileField(
        help_text='이미지는 최대 5개까지 업로드할 수 있습니다.',
    )

    def __init__(self, *args, existing_image_count=0, **kwargs):
        self.existing_image_count = existing_image_count
        super().__init__(*args, **kwargs)
        self.fields['content'].widget.attrs.setdefault('maxlength', 1000)
        self.fields['content'].widget.attrs.setdefault('data-maxlength', 1000)

    class Meta:
        model = Review
        fields = ('rating', 'content')
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5, 'placeholder': '상품에 대한 솔직한 후기를 남겨주세요.'}),
            'rating': forms.HiddenInput(),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating is None:
            raise forms.ValidationError('평점을 선택해주세요.')

        if not (Review.MIN_RATING <= rating <= Review.MAX_RATING):
            raise forms.ValidationError('평점은 1점에서 5점 사이여야 합니다.')
        return rating

    def clean_content(self):
        content = self.cleaned_data.get('content') or ''
        content = content.strip()
        if not content:
            raise forms.ValidationError('후기 내용을 입력해주세요.')
        if len(content) > 1000:
            content = content[:1000]
        return content

    def clean_images(self):
        images = self.cleaned_data.get('images') or []
        total_images = self.existing_image_count + len(images)
        if total_images > 5:
            raise forms.ValidationError('이미지는 최대 5개까지 업로드할 수 있습니다.')
        return images
