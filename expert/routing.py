from django.urls import path

from .consumers import ContractChatConsumer

websocket_urlpatterns = [
    path("ws/expert/contracts/<uuid:contract_id>/chat/", ContractChatConsumer.as_asgi()),
]
