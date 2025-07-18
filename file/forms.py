from django import forms
from django.core.exceptions import ValidationError
from .models import DigitalFile


class DigitalFileForm(forms.ModelForm):
    """디지털 파일 추가/수정 폼"""
    
    class Meta:
        model = DigitalFile
        fields = [
            'name', 'description', 'file', 'preview_image',
            'price_display', 'price', 'price_krw', 
            'is_discounted', 'discounted_price', 'discounted_price_krw',
            'discount_end_date', 'discount_end_time',
            'max_downloads', 'download_expiry_days',
            'purchase_message'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': '파일명을 입력하세요'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'rows': 10,
                'placeholder': '파일에 대한 자세한 설명을 마크다운 형식으로 작성하세요'
            }),
            'file': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-bitcoin file:text-white hover:file:bg-bitcoin-dark',
                'accept': '*/*'
            }),
            'preview_image': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-bitcoin file:text-white hover:file:bg-bitcoin-dark',
                'accept': 'image/*'
            }),
            'price_display': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': '0',
                'min': '0'
            }),
            'price_krw': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': '0',
                'min': '0'
            }),
            'is_discounted': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-bitcoin bg-gray-100 border-gray-300 rounded focus:ring-bitcoin focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
            }),
            'discounted_price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': '0',
                'min': '0'
            }),
            'discounted_price_krw': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': '0',
                'min': '0'
            }),
            'discount_end_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'type': 'date'
            }),
            'discount_end_time': forms.TimeInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'type': 'time',
                'value': '23:59'
            }),
            'max_downloads': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': '비워두면 무제한',
                'min': '0'
            }),
            'download_expiry_days': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': '비워두면 무제한',
                'min': '0'
            }),
            'purchase_message': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'rows': 4,
                'placeholder': '구매 완료 후 보여줄 메시지를 입력하세요 (마크다운 지원)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 기본값 설정
        if not self.instance.pk:  # 새로 생성하는 경우
            self.fields['price_display'].initial = 'free'
            self.fields['price'].initial = 0
            self.fields['price_krw'].initial = 0
    
    def clean(self):
        cleaned_data = super().clean()
        price_display = cleaned_data.get('price_display')
        price = cleaned_data.get('price')
        price_krw = cleaned_data.get('price_krw')
        is_discounted = cleaned_data.get('is_discounted')
        discounted_price = cleaned_data.get('discounted_price')
        discounted_price_krw = cleaned_data.get('discounted_price_krw')
        discount_end_date = cleaned_data.get('discount_end_date')
        file = cleaned_data.get('file')
        
        # 새로 생성하는 경우 파일은 필수
        if not self.instance.pk and not file:
            raise ValidationError('파일을 업로드해야 합니다.')
        
        # 가격이 None인 경우 0으로 설정
        if price is None:
            cleaned_data['price'] = 0
            price = 0
        
        if price_krw is None:
            cleaned_data['price_krw'] = 0
            price_krw = 0
        
        if discounted_price is None:
            cleaned_data['discounted_price'] = 0
            discounted_price = 0
        
        if discounted_price_krw is None:
            cleaned_data['discounted_price_krw'] = 0
            discounted_price_krw = 0
        
        # 가격 옵션별 검증
        if price_display == 'free':
            cleaned_data['price'] = 0
            cleaned_data['price_krw'] = 0
            cleaned_data['is_discounted'] = False
            cleaned_data['discounted_price'] = 0
            cleaned_data['discounted_price_krw'] = 0
            cleaned_data['discount_end_date'] = None
            cleaned_data['discount_end_time'] = None
        elif price_display == 'sats':
            cleaned_data['price_krw'] = 0
            cleaned_data['discounted_price_krw'] = 0
            if price <= 0:
                raise ValidationError('사토시 가격은 0보다 커야 합니다.')
            
            # 할인 관련 검증
            if is_discounted:
                if discounted_price is None or discounted_price < 0:
                    raise ValidationError('할인을 적용하려면 유효한 사토시 할인가를 입력해야 합니다.')
                if not discount_end_date:
                    raise ValidationError('할인을 적용하려면 할인 종료일을 입력해야 합니다.')
                if discounted_price >= price:
                    raise ValidationError('할인가는 정가보다 낮아야 합니다.')
        elif price_display == 'krw':
            cleaned_data['price'] = 0
            cleaned_data['discounted_price'] = 0
            if price_krw <= 0:
                raise ValidationError('원화 가격은 0보다 커야 합니다.')
            
            # 할인 관련 검증
            if is_discounted:
                if discounted_price_krw is None or discounted_price_krw < 0:
                    raise ValidationError('할인을 적용하려면 유효한 원화 할인가를 입력해야 합니다.')
                if not discount_end_date:
                    raise ValidationError('할인을 적용하려면 할인 종료일을 입력해야 합니다.')
                if discounted_price_krw >= price_krw:
                    raise ValidationError('할인가는 정가보다 낮아야 합니다.')
        
        return cleaned_data