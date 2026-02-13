from django import forms

from .models import ApiKey
from .nostr_auth import NostrAuthError, normalize_nostr_pubkey


class ApiKeyAdminForm(forms.ModelForm):
    use_nostr_auth = forms.BooleanField(
        required=False,
        label="Nostr 인증 사용",
        help_text="체크하면 Bearer API 키 대신 Nostr 서명 검증으로 인증합니다.",
    )
    nostr_pubkey_input = forms.CharField(
        required=False,
        label="Nostr 공개키",
        help_text="허용할 상대 공개키 입력(64자리 hex 또는 npub).",
    )

    class Meta:
        model = ApiKey
        fields = ("name", "channel_slug", "scopes", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, "instance", None)
        if not instance or not instance.pk:
            return

        self.fields["use_nostr_auth"].initial = instance.uses_nostr_auth
        if instance.nostr_pubkey:
            self.fields["nostr_pubkey_input"].initial = instance.nostr_pubkey

    def clean(self):
        cleaned_data = super().clean()
        use_nostr_auth = cleaned_data.get("use_nostr_auth")
        pubkey_input = (cleaned_data.get("nostr_pubkey_input") or "").strip()

        if not use_nostr_auth:
            cleaned_data["normalized_nostr_pubkey"] = ""
            return cleaned_data

        if not pubkey_input:
            self.add_error("nostr_pubkey_input", "Nostr 인증을 선택하면 공개키를 입력해야 합니다.")
            return cleaned_data

        try:
            normalized_pubkey = normalize_nostr_pubkey(pubkey_input)
        except NostrAuthError as exc:
            self.add_error("nostr_pubkey_input", str(exc))
            return cleaned_data

        cleaned_data["normalized_nostr_pubkey"] = normalized_pubkey
        return cleaned_data
