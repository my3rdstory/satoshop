from __future__ import annotations

import re
from typing import List

from django import forms

from .models import BahPromotionRequest, MAX_PROMOTION_IMAGES


PHONE_RE = re.compile(r'^[0-9+\-\s()]{6,20}$')
MAX_IMAGE_SIZE_MB = 5
ALLOWED_IMAGE_CONTENT_TYPES = {
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif',
}


class MultiFileInput(forms.ClearableFileInput):
    """다중 파일 업로드 지원 위젯"""

    allow_multiple_selected = True


class BahPromotionRequestForm(forms.ModelForm):
    """BAH 홍보요청 입력 폼"""

    images = forms.FileField(
        label='매장 홍보 사진',
        required=False,
        widget=MultiFileInput(
            attrs={
                'multiple': True,
                'accept': 'image/*',
            }
        ),
        help_text=f'최대 {MAX_PROMOTION_IMAGES}장까지 업로드할 수 있습니다.',
    )
    accept_privacy = forms.BooleanField(
        label='위 신청을 위해 개인정보 수집·이용에 동의합니다.',
        required=True,
    )

    def __init__(self, *args, existing_image_count: int = 0, **kwargs):
        self.existing_image_count = existing_image_count
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            if name not in {'images', 'accept_privacy'}:
                field.required = True

        # Tailwind 기반 폼 스타일링을 위해 공통 클래스 적용
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault(
                    'class',
                    'w-full rounded-lg border border-gray-300 dark:border-gray-600 '
                    'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 '
                    'focus:ring-bitcoin focus:border-bitcoin placeholder-gray-400 '
                    'text-sm px-3 py-2 transition-colors duration-150',
                )
                field.widget.attrs.setdefault('rows', 5)
            elif isinstance(field.widget, forms.ClearableFileInput):
                field.widget.attrs.setdefault(
                    'class',
                    'w-full text-sm text-gray-500 dark:text-gray-300 '
                    'file:mr-4 file:py-2 file:px-4 file:rounded-lg '
                    'file:border-0 file:text-sm file:font-semibold '
                    'file:bg-bitcoin file:text-white hover:file:bg-bitcoin/90',
                )
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault(
                    'class',
                    'mt-1 h-4 w-4 text-bitcoin focus:ring-bitcoin border-gray-300 rounded'
                )
            else:
                field.widget.attrs.setdefault(
                    'class',
                    'w-full rounded-lg border border-gray-300 dark:border-gray-600 '
                    'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 '
                    'focus:ring-bitcoin focus:border-bitcoin placeholder-gray-400 '
                    'text-sm px-3 py-2 transition-colors duration-150',
                )

        self.fields['store_name'].widget.attrs.setdefault('placeholder', '예) 비트코인 허브 카페')
        self.fields['address'].widget.attrs.setdefault('placeholder', '도로명 주소 검색으로 자동 입력')
        self.fields['address_detail'].widget.attrs.setdefault('placeholder', '건물/층/호수 등 상세 정보를 입력해주세요')
        self.fields['phone_number'].widget.attrs.setdefault('placeholder', '예) 02-123-4567 또는 010-1234-5678')
        self.fields['email'].widget.attrs.setdefault('placeholder', '홍보 진행 관련 안내를 받을 이메일 주소')
        self.fields['introduction'].widget.attrs.setdefault('placeholder', '매장의 비트코인 결제 경험과 특징을 간단히 소개해주세요.')
        self.fields['postal_code'].widget.attrs.setdefault('data-address-trigger', 'true')
        self.fields['address'].widget.attrs.setdefault('data-address-trigger', 'true')
        self.fields['accept_privacy'].error_messages['required'] = '개인정보 수집·이용에 동의해야 신청할 수 있습니다.'

    class Meta:
        model = BahPromotionRequest
        fields = [
            'store_name',
            'postal_code',
            'address',
            'address_detail',
            'phone_number',
            'email',
            'introduction',
        ]
        labels = {
            'store_name': '매장명',
            'postal_code': '우편번호',
            'address': '매장 주소',
            'address_detail': '상세 주소',
            'phone_number': '매장 전화번호',
            'email': '이메일',
            'introduction': '매장 소개 문구',
        }
        help_texts = {
            'postal_code': '주소검색 버튼으로 자동 입력됩니다.',
            'address': '주소 검색으로 찾아주세요. 지번/도로명 모두 가능합니다.',
            'introduction': '최대 1,500자까지 작성할 수 있습니다.',
        }

    def clean_phone_number(self) -> str:
        value = self.cleaned_data['phone_number'].strip()
        if not PHONE_RE.match(value):
            raise forms.ValidationError('전화번호 형식을 다시 확인해주세요.')
        return value

    def clean_introduction(self) -> str:
        value = self.cleaned_data['introduction'].strip()
        if len(value) > 1500:
            raise forms.ValidationError('소개 문구는 1,500자 이하로 작성해주세요.')
        return value

    def clean_images(self) -> List:
        raw_files: List = list(self.files.getlist('images') or [])

        if not raw_files:
            for field_name, value_list in self.files.lists():
                if field_name == 'images' or field_name.startswith('images['):
                    if not value_list:
                        continue
                    raw_files.extend(uploaded for uploaded in value_list if uploaded)

        files: List = [uploaded for uploaded in raw_files if uploaded]

        if not files:
            return []

        if self.existing_image_count + len(files) > MAX_PROMOTION_IMAGES:
            raise forms.ValidationError(
                f'이미지는 최대 {MAX_PROMOTION_IMAGES}장까지 업로드할 수 있습니다.'
            )

        for uploaded in files:
            if uploaded.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
                raise forms.ValidationError('이미지 파일(JPEG, PNG, WEBP, GIF)만 업로드해주세요.')
            if uploaded.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
                raise forms.ValidationError(
                    f'각 이미지 크기는 {MAX_IMAGE_SIZE_MB}MB를 초과할 수 없습니다.'
                )
        return files

    def get_uploaded_images(self) -> List:
        return self.cleaned_data.get('images', [])
