from django import forms
from django.core.exceptions import ValidationError
from .models import Meetup, MeetupImage, MeetupOption, MeetupChoice

class MeetupForm(forms.ModelForm):
    """밋업 추가/수정 폼"""
    
    # 이미지 업로드
    images = forms.ImageField(
        required=False,
        label="밋업 이미지",
        widget=forms.FileInput(attrs={'accept': 'image/*'})
    )
    
    class Meta:
        model = Meetup
        fields = [
            'name', 'description', 'date_time', 
            'location_postal_code', 'location_address', 'location_detail_address', 'location_tbd', 'special_notes',
            'organizer_contact', 'organizer_email', 'organizer_chat_channel',
            'price', 'is_discounted', 'discounted_price',
            'early_bird_end_date', 'early_bird_end_time', 'max_participants',
            'completion_message'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': '밋업명을 입력하세요'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'rows': 10,
                'placeholder': '밋업에 대한 자세한 설명을 마크다운 형식으로 작성하세요'
            }),
            'date_time': forms.DateTimeInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'type': 'datetime-local'
            }),
            'location_postal_code': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-600',
                'placeholder': '클릭하여 주소 검색',
                'readonly': True
            }),
            'location_address': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-600',
                'placeholder': '클릭하여 주소 검색',
                'readonly': True
            }),
            'location_detail_address': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white transition-colors',
                'placeholder': '아파트명, 동/호수 등 상세주소를 입력하세요'
            }),
            'location_tbd': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-bitcoin bg-gray-100 border-gray-300 rounded focus:ring-bitcoin focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
            }),
            'special_notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white transition-colors',
                'rows': 4,
                'placeholder': '특이사항이 있으면 입력하세요 (선택사항)'
            }),
            'organizer_contact': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': '010-1234-5678'
            }),
            'organizer_email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': 'organizer@example.com'
            }),
            'organizer_chat_channel': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': '예: https://open.kakao.com/o/abcd1234'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': '0',
                'min': '0'
            }),
            'discounted_price': forms.NumberInput(attrs={
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
            'max_participants': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': '제한 없음',
                'min': '1'
            }),
            'completion_message': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'rows': 4,
                'placeholder': '참가 신청 완료 후 보여줄 메시지를 입력하세요'
            }),
            'is_discounted': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-bitcoin bg-gray-100 border-gray-300 rounded focus:ring-bitcoin focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get('price')
        is_discounted = cleaned_data.get('is_discounted')
        discounted_price = cleaned_data.get('discounted_price')
        early_bird_end_date = cleaned_data.get('early_bird_end_date')
        organizer_contact = cleaned_data.get('organizer_contact')
        organizer_email = cleaned_data.get('organizer_email')
        
        # 가격이 None인 경우 0으로 설정
        if price is None:
            cleaned_data['price'] = 0
            price = 0
        
        if discounted_price is None:
            cleaned_data['discounted_price'] = 0
            discounted_price = 0
        
        # 할인 관련 검증 (가격이 0인 경우 할인 검증 스킵)
        if is_discounted and price > 0:
            if discounted_price is None or discounted_price < 0:
                raise ValidationError('할인을 적용하려면 유효한 할인가를 입력해야 합니다.')
            if not early_bird_end_date:
                raise ValidationError('할인을 적용하려면 조기등록 종료일을 입력해야 합니다.')
            if discounted_price >= price:
                raise ValidationError('할인가는 정가보다 낮아야 합니다.')
        elif is_discounted and price == 0:
            # 무료 밋업에서 할인이 체크되어 있으면 할인 해제
            cleaned_data['is_discounted'] = False
            cleaned_data['discounted_price'] = 0
        
        # 주최자 연락처 검증 (연락처나 이메일 중 하나는 필수)
        if not organizer_contact and not organizer_email:
            raise ValidationError('주최자 연락처 또는 이메일 중 하나는 필수입니다.')
        
        return cleaned_data 