from functools import wraps
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Store


def store_owner_required(view_func):
    """
    스토어 소유자만 접근할 수 있도록 하는 데코레이터
    URL에서 store_id를 받아서 해당 스토어의 소유자인지 확인
    
    수퍼어드민의 경우 'admin_access=true' 파라미터를 통해 다른 스토어에 접근 가능
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, store_id, *args, **kwargs):
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        
        # 수퍼어드민 특별 접근 확인
        admin_access = request.GET.get('admin_access', '').lower() == 'true'
        is_superuser = request.user.is_superuser
        
        # 스토어 소유자이거나 수퍼어드민이 admin_access 파라미터를 사용한 경우 접근 허용
        if store.owner == request.user or (is_superuser and admin_access):
            # 수퍼어드민이 다른 스토어에 접근하는 경우 알림 메시지 표시
            if is_superuser and admin_access and store.owner != request.user:
                messages.info(request, f'관리자 권한으로 "{store.store_name}" 스토어에 접근 중입니다.')
            
            return view_func(request, store_id, *args, **kwargs)
        else:
            if is_superuser:
                # 수퍼어드민인 경우 admin_access 파라미터 사용법 안내
                messages.error(request, 
                    '스토어 소유자만 접근할 수 있습니다. '
                    '관리자 권한으로 접근하려면 URL에 "?admin_access=true" 파라미터를 추가하세요.')
            else:
                messages.error(request, '스토어 소유자만 접근할 수 있습니다.')
            return redirect('myshop:home')
    
    return _wrapped_view 