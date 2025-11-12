"""
ASGI config for satoshop project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'satoshop.settings')

django_asgi_app = get_asgi_application()

try:
    from expert.routing import websocket_urlpatterns as expert_websocket_urlpatterns
except Exception:
    expert_websocket_urlpatterns = []

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            expert_websocket_urlpatterns
        )
    ),
})
