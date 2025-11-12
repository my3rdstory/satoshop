import json
import uuid
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Contract, ContractMessage, ContractParticipant

User = get_user_model()


class ContractChatConsumer(AsyncWebsocketConsumer):
    """계약서 페이지 실시간 채팅 Consumer."""

    async def connect(self):
        user = self.scope["user"]
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        contract_id = self.scope["url_route"]["kwargs"].get("contract_id")
        try:
            self.contract_uuid = uuid.UUID(contract_id)
        except (TypeError, ValueError):
            await self.close(code=4400)
            return

        contract = await self._get_contract(self.contract_uuid)
        if contract is None:
            await self.close(code=4404)
            return

        participant = await self._get_participant(contract, user)
        if participant is None and not user.is_staff:
            await self.close(code=4403)
            return

        self.contract = contract
        self.participant_role = participant.role if participant else "staff"
        self.group_name = contract.channel_group_name

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat.system",
                "message": f"{user.get_full_name() or user.username}님이 채팅에 접속했습니다.",
                "timestamp": timezone.now().isoformat(),
            },
        )

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        data = json.loads(text_data)
        message = data.get("message", "").strip()
        if not message:
            return

        if len(message) > 2000:
            message = message[:2000]

        message_obj = await self._save_message(
            contract=self.contract,
            sender=self.scope["user"],
            role=self.participant_role,
            content=message,
        )

        payload = {
            "type": "chat.message",
            "message": message_obj.content,
            "sender": message_obj.sender.get_full_name()
            or message_obj.sender.username
            if message_obj.sender
            else "시스템",
            "sender_role": message_obj.sender_role,
            "timestamp": message_obj.created_at.isoformat(),
        }
        await self.channel_layer.group_send(self.group_name, payload)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    async def chat_system(self, event):
        await self.send(text_data=json.dumps({**event, "type": "chat.system"}))

    @database_sync_to_async
    def _get_contract(self, contract_uuid):
        try:
            return Contract.objects.get(public_id=contract_uuid)
        except Contract.DoesNotExist:
            return None

    @database_sync_to_async
    def _get_participant(self, contract, user):
        try:
            return contract.participants.get(user=user)
        except ContractParticipant.DoesNotExist:
            return None

    @database_sync_to_async
    def _save_message(self, contract, sender, role, content):
        return ContractMessage.objects.create(
            contract=contract,
            sender=sender,
            sender_role=role if role != "staff" else "",
            content=content,
        )
