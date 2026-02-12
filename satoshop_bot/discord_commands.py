from __future__ import annotations

import logging

import requests

from .models import DiscordBot

logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"

SLASH_COMMANDS = [
    {
        "name": "사토샵_최근등록상품",
        "description": "사토샵 전체 최근 등록 아이템 20개를 보여줍니다.",
    },
    {
        "name": "사토샵_최근판매상품",
        "description": "사토샵 전체 최근 판매 아이템 20개를 보여줍니다.",
    },
]


def sync_discord_application_commands(bot: DiscordBot, *, timeout: int = 10) -> list[dict]:
    if not bot.application_id:
        raise ValueError("application_id가 설정되지 않았습니다.")
    if not bot.token:
        raise ValueError("봇 토큰이 설정되지 않았습니다.")

    url = f"{DISCORD_API_BASE}/applications/{bot.application_id}/commands"
    headers = {
        "Authorization": f"Bot {bot.token}",
        "Content-Type": "application/json",
    }
    response = requests.put(url, headers=headers, json=SLASH_COMMANDS, timeout=timeout)
    if response.status_code >= 400:
        logger.warning(
            "디스코드 슬래시 명령어 동기화 실패 status=%s body=%s",
            response.status_code,
            response.text,
        )
        raise RuntimeError(f"디스코드 명령어 동기화 실패: {response.status_code}")

    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError("디스코드 응답 형식이 올바르지 않습니다.")
    return payload
