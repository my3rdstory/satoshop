from django import forms
from django.core.exceptions import ValidationError
from .models import LiveLecture, LiveLectureImage

class LiveLectureForm(forms.ModelForm):
    """라이브 강의 추가/수정 폼"""
    
    # 이미지 업로드
    images = forms.ImageField(
        required=False,
        label="커버 이미지",
        widget=forms.FileInput(attrs={'accept': 'image/*'})
    )
    
    class Meta:
        model = LiveLecture
        fields = [
            'name', 'description', 'date_time', 'special_notes',
            'instructor_contact', 'instructor_email', 'instructor_chat_channel',
            'max_participants', 'no_limit',
            'price_display', 'price', 'price_krw', 
            'is_discounted', 'discounted_price', 'discounted_price_krw',
            'early_bird_end_date', 'early_bird_end_time',
            'completion_message'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': '라이브 강의명을 입력하세요'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'rows': 10,
                'placeholder': '라이브 강의에 대한 자세한 설명을 마크다운 형식으로 작성하세요'
            }),
            'date_time': forms.DateTimeInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'type': 'datetime-local'
            }),
            'special_notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white transition-colors',
                'rows': 4,
                'placeholder': '특이사항이 있으면 입력하세요 (선택사항)'
            }),
            'instructor_contact': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': '010-1234-5678'
            }),
            'instructor_email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': 'instructor@example.com'
            }),
            'instructor_chat_channel': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': '예: https://meet.google.com/abc-defg-hij'
            }),
            'max_participants': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': '예: 20',
                'min': '1'
            }),
            'no_limit': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-bitcoin bg-gray-100 border-gray-300 rounded focus:ring-bitcoin focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
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
            'early_bird_end_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'type': 'date'
            }),
            'early_bird_end_time': forms.TimeInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'type': 'time',
                'value': '23:59'
            }),
            'completion_message': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'rows': 4,
                'placeholder': '참가 신청 완료 후 보여줄 메시지를 입력하세요'
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
        early_bird_end_date = cleaned_data.get('early_bird_end_date')
        instructor_contact = cleaned_data.get('instructor_contact')
        instructor_email = cleaned_data.get('instructor_email')
        no_limit = cleaned_data.get('no_limit')
        max_participants = cleaned_data.get('max_participants')
        
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
        
        # 정원 체크
        if no_limit:
            cleaned_data['max_participants'] = None
        elif not max_participants:
            raise ValidationError('정원을 설정하거나 정원 없음을 체크해야 합니다.')
        
        # 가격 옵션별 검증
        if price_display == 'free':
            cleaned_data['price'] = 0
            cleaned_data['price_krw'] = 0
            cleaned_data['is_discounted'] = False
            cleaned_data['discounted_price'] = 0
            cleaned_data['discounted_price_krw'] = 0
            cleaned_data['early_bird_end_date'] = None
            cleaned_data['early_bird_end_time'] = None
        elif price_display == 'sats':
            cleaned_data['price_krw'] = 0
            cleaned_data['discounted_price_krw'] = 0
            if price <= 0:
                raise ValidationError('사토시 가격은 0보다 커야 합니다.')
            
            # 할인 관련 검증
            if is_discounted:
                if discounted_price is None or discounted_price < 0:
                    raise ValidationError('할인을 적용하려면 유효한 사토시 할인가를 입력해야 합니다.')
                if not early_bird_end_date:
                    raise ValidationError('할인을 적용하려면 조기등록 종료일을 입력해야 합니다.')
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
                if not early_bird_end_date:
                    raise ValidationError('할인을 적용하려면 조기등록 종료일을 입력해야 합니다.')
                if discounted_price_krw >= price_krw:
                    raise ValidationError('할인가는 정가보다 낮아야 합니다.')
        
        # 강사 연락처 검증 (연락처나 이메일 중 하나는 필수)
        if not instructor_contact and not instructor_email:
            raise ValidationError('강사 연락처 또는 이메일 중 하나는 필수입니다.')
        
        return cleaned_data 