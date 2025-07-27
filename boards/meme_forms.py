from django import forms
from .models import MemePost, MemeTag


class MemePostForm(forms.ModelForm):
    """밈 게시글 폼"""
    new_tags = forms.CharField(
        label='새 태그', 
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full px-3 py-2 text-sm rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': '새 태그를 입력하세요 (쉼표로 구분)'
        }),
        help_text='여러 태그는 쉼표로 구분하세요'
    )
    
    class Meta:
        model = MemePost
        fields = ['title', 'tags']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input w-full px-3 py-2 text-sm rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': '제목을 입력하세요'
            }),
            'tags': forms.CheckboxSelectMultiple(attrs={
                'class': 'meme-tag-checkbox'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tags'].required = False
        self.fields['tags'].queryset = MemeTag.objects.all().order_by('name')
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if commit:
            instance.save()
            
            # 기존 태그 저장
            self.save_m2m()
            
            # 새 태그 처리
            new_tags_str = self.cleaned_data.get('new_tags', '')
            if new_tags_str:
                new_tags = [tag.strip() for tag in new_tags_str.split(',') if tag.strip()]
                for tag_name in new_tags:
                    tag, created = MemeTag.objects.get_or_create(name=tag_name)
                    instance.tags.add(tag)
        
        return instance