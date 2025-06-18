from django import forms
from .models import Notice, NoticeComment


class NoticeForm(forms.ModelForm):
    """공지사항 작성/수정 폼"""
    
    class Meta:
        model = Notice
        fields = ['title', 'content', 'is_pinned']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '공지사항 제목을 입력하세요',
                'maxlength': 200
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': '공지사항 내용을 입력하세요',
                'rows': 10
            }),
            'is_pinned': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            })
        }
        labels = {
            'title': '제목',
            'content': '내용',
            'is_pinned': '상단 고정'
        }


class NoticeCommentForm(forms.ModelForm):
    """공지사항 댓글 작성/수정 폼"""
    
    class Meta:
        model = NoticeComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'comment-textarea',
                'placeholder': '댓글을 입력하세요',
                'rows': 4
            })
        }
        labels = {
            'content': '댓글 내용'
        } 