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
            purchase_apps = []
            accounts_apps = []
            others = []

            purchase_priority = {
                'OrderCleanupProxy': 0,
                'MeetupOrderCleanupProxy': 1,
                'LiveLectureOrderCleanupProxy': 2,
                'FileOrderCleanupProxy': 3,
            }
            account_priority = {
                'LightningUser': 0,
                'UserMyPageHistory': 1,
                'UserPurchaseHistory': 2,
            }

            for app in app_list:
                label = app.get('app_label')
                name = app.get('name') or ''
                models = app.get('models', [])

                purchase_models = {'상품 구입 이력', '밋업 구입 이력', '라이브 강의 구입 이력', '디지털 파일 구입 이력'}

                is_purchase_app = any(model.get('name') in purchase_models for model in models)
                if is_purchase_app:
                    # 새 카테고리명으로 표시
                    app_copy = app.copy()
                    app_copy['name'] = '구입 이력 관리'
                    sorted_models = sorted(
                        models,
                        key=lambda m: purchase_priority.get(m.get('object_name'), 999),
                    )
                    app_copy['models'] = sorted_models
                    purchase_apps.append(app_copy)
                elif label == 'accounts':
                    sorted_models = sorted(
                        models,
                        key=lambda m: account_priority.get(m.get('object_name'), 999),
                    )
                    app_copy = app.copy()
                    app_copy['models'] = sorted_models
                    accounts_apps.append(app_copy)
                else:
                    others.append(app)

            # 구입 이력 관리 > 사용자 계정 > 나머지 순서
            return purchase_apps + accounts_apps + others

        admin.site.get_app_list = get_app_list
        admin.site._accounts_app_list_patched = True
