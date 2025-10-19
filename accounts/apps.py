from django.apps import AppConfig
from functools import wraps


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = '사용자 계정'

    def ready(self):
        from django.contrib import admin

        if getattr(admin.site, '_accounts_app_list_patched', False):
            return

        original_get_app_list = admin.site.get_app_list

        @wraps(original_get_app_list)
        def get_app_list(request):
            app_list = original_get_app_list(request)
            prioritized = [app for app in app_list if app.get('app_label') == 'accounts']
            others = [app for app in app_list if app.get('app_label') != 'accounts']
            return prioritized + others

        admin.site.get_app_list = get_app_list
        admin.site._accounts_app_list_patched = True
