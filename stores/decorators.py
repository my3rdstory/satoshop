from functools import wraps
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Store


def store_owner_required(view_func):
    """
    스토어 소유자만 접근할 수 있도록 하는 데코레이터
    URL에서 store_id를 받아서 해당 스토어의 소유자인지 확인
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, store_id, *args, **kwargs):
        store = get_object_or_404(Store, store_id=store_id, deleted_at__isnull=True)
        
        if store.owner != request.user:
            messages.error(request, '스토어 소유자만 접근할 수 있습니다.')
            return redirect('myshop:home')
        
        return view_func(request, store_id, *args, **kwargs)
    
    return _wrapped_view 