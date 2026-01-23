from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


User = get_user_model()


class LightningAccountLinkForm(forms.Form):
    username = forms.CharField(
        label=_('아이디'),
        max_length=User._meta.get_field('username').max_length,
        validators=User._meta.get_field('username').validators,
        help_text=_('다른 사용자와 중복되지 않게 입력하세요.'),
        widget=forms.TextInput(attrs={
            'autocomplete': 'username',
            'spellcheck': 'false',
        }),
    )
    password1 = forms.CharField(
        label=_('비밀번호'),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label=_('비밀번호 확인'),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username=username).exclude(pk=self.user.pk).exists():
            raise ValidationError(_('이미 사용 중인 아이디입니다.'))
        return username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', _('비밀번호가 일치하지 않습니다.'))

        if password1:
            try:
                validate_password(password1, self.user)
            except ValidationError as exc:
                self.add_error('password1', exc)

        return cleaned_data

    def save(self):
        self.user.username = self.cleaned_data['username']
        self.user.set_password(self.cleaned_data['password1'])
        self.user.save(update_fields=['username', 'password'])
        return self.user


class LocalAccountUsernameCheckForm(forms.Form):
    username = forms.CharField(
        label=_('아이디'),
        max_length=User._meta.get_field('username').max_length,
        validators=User._meta.get_field('username').validators,
        error_messages={
            'required': _('아이디를 입력하세요.'),
        },
        widget=forms.TextInput(attrs={
            'autocomplete': 'username',
            'spellcheck': 'false',
        }),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username=username).exclude(pk=self.user.pk).exists():
            raise ValidationError(_('이미 사용 중인 아이디입니다.'))
        return username
