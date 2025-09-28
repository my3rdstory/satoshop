from django import forms

from .models import Review


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class ReviewForm(forms.ModelForm):
    images = forms.FileField(
        required=False,
        widget=MultiFileInput(attrs={'multiple': True}),
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
            raise forms.ValidationError('1000자 이하로 작성해주세요.')
        return content

    def clean_images(self):
        images = self.files.getlist('images')
        total_images = self.existing_image_count + len(images)
        if total_images > 5:
            raise forms.ValidationError('이미지는 최대 5개까지 업로드할 수 있습니다.')
        return images
