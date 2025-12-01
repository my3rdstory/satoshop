from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

class TemporaryPasswordBackend(ModelBackend):
    """임시 비밀번호로 로그인 가능하도록 하는 백엔드"""

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        username = username or kwargs.get(UserModel.USERNAME_FIELD)

        if not username or not password:
            return None

        try:
            user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            # 기본 동작과 맞추기 위해 패스워드 해시 계산 시도를 수행
            UserModel().set_password(password)
            return None

        temp_password = getattr(user, 'temporary_password_credential', None)
        if temp_password and temp_password.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
