from django import forms
from django.core.exceptions import ValidationError
from .models import Menu, MenuCategory, MenuOption
import json

class MenuCategoryForm(forms.ModelForm):
    class Meta:
        model = MenuCategory
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white',
                'placeholder': '카테고리명을 입력하세요',
                'maxlength': 50
            })
        }

    def __init__(self, *args, **kwargs):
        self.store = kwargs.pop('store', None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError('카테고리명을 입력해주세요.')
        
        # 같은 스토어 내에서 중복 체크
        if self.store:
            existing = MenuCategory.objects.filter(
                store=self.store, 
                name=name
            )
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('이미 존재하는 카테고리명입니다.')
        
        return name

class MenuForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(
        queryset=MenuCategory.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='카테고리'
    )

    class Meta:
        model = Menu
        fields = [
            'name', 'description', 'image', 'categories', 'price_display', 
            'price', 'is_discounted', 'discounted_price'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'placeholder': '메뉴명을 입력하세요'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'rows': 10,
                'placeholder': '메뉴에 대한 자세한 설명을 마크다운 형식으로 작성하세요'
            }),
            'image': forms.FileInput(attrs={
                'class': 'hidden',
                'accept': 'image/*'
            }),
            'price_display': forms.RadioSelect(attrs={
                'class': 'w-4 h-4 text-bitcoin bg-gray-100 border-gray-300 focus:ring-bitcoin dark:focus:ring-bitcoin dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 pr-16 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'min': '0',
                'placeholder': '메뉴 가격을 입력하세요'
            }),
            'is_discounted': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-bitcoin bg-gray-100 border-gray-300 rounded focus:ring-bitcoin dark:focus:ring-bitcoin dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
            }),
            'discounted_price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 pr-16 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400',
                'min': '0',
                'placeholder': '할인가를 입력하세요'
            })
        }

    def __init__(self, *args, **kwargs):
        self.store = kwargs.pop('store', None)
        super().__init__(*args, **kwargs)
        
        # 해당 스토어의 카테고리만 표시
        if self.store:
            self.fields['categories'].queryset = MenuCategory.objects.filter(store=self.store)

    def clean(self):
        cleaned_data = super().clean()
        is_discounted = cleaned_data.get('is_discounted')
        price = cleaned_data.get('price')
        discounted_price = cleaned_data.get('discounted_price')

        if is_discounted:
            if discounted_price is None:
                raise ValidationError('할인 적용 시 할인가를 입력해야 합니다.')
            if price is not None and discounted_price is not None and discounted_price >= price:
                raise ValidationError('할인가는 정가보다 낮아야 합니다.')

        return cleaned_data



class MenuOptionForm(forms.ModelForm):
    values_input = forms.CharField(
        label='옵션값 (콤마로 구분)',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white',
            'placeholder': '예: 소, 중, 대'
        }),
        required=False
    )

    class Meta:
        model = MenuOption
        fields = ['name', 'is_required', 'order']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white',
                'placeholder': '예: 사이즈, 맵기 정도'
            }),
            'is_required': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-bitcoin bg-gray-100 border-gray-300 rounded focus:ring-bitcoin dark:focus:ring-bitcoin dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white',
                'min': '0'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.values:
            # 기존 옵션값들을 콤마로 구분된 문자열로 표시
            values_list = self.instance.values_list
            self.fields['values_input'].initial = ', '.join(values_list)

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # 콤마로 구분된 문자열을 리스트로 변환하여 저장
        values_input = self.cleaned_data.get('values_input', '')
        if values_input:
            values_list = [v.strip() for v in values_input.split(',') if v.strip()]
            instance.set_values_list(values_list)
        else:
            instance.values = '[]'
        
        if commit:
            instance.save()
        return instance 