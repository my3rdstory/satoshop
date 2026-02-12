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


def _build_headers(bot: DiscordBot) -> dict:
    return {
        "Authorization": f"Bot {bot.token}",
        "Content-Type": "application/json",
    }


def _sync_global_commands(bot: DiscordBot, *, timeout: int) -> list[dict]:
    url = f"{DISCORD_API_BASE}/applications/{bot.application_id}/commands"
    response = requests.put(url, headers=_build_headers(bot), json=SLASH_COMMANDS, timeout=timeout)
    if response.status_code >= 400:
        logger.warning(
            "디스코드 글로벌 명령어 동기화 실패 status=%s body=%s",
            response.status_code,
            response.text,
        )
        raise RuntimeError(f"디스코드 글로벌 명령어 동기화 실패: {response.status_code}")
    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError("디스코드 글로벌 명령어 응답 형식이 올바르지 않습니다.")
    return payload


def _sync_guild_commands(bot: DiscordBot, *, guild_id: str, timeout: int) -> list[dict]:
    url = f"{DISCORD_API_BASE}/applications/{bot.application_id}/guilds/{guild_id}/commands"
    response = requests.put(url, headers=_build_headers(bot), json=SLASH_COMMANDS, timeout=timeout)
    if response.status_code >= 400:
        logger.warning(
            "디스코드 길드 명령어 동기화 실패 guild=%s status=%s body=%s",
            guild_id,
            response.status_code,
            response.text,
        )
        raise RuntimeError(f"디스코드 길드 명령어 동기화 실패(guild={guild_id}): {response.status_code}")
    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError(f"디스코드 길드 명령어 응답 형식이 올바르지 않습니다(guild={guild_id}).")
    return payload


def fetch_bot_guild_ids(bot: DiscordBot, *, timeout: int = 10) -> list[str]:
    if not bot.token:
        raise ValueError("봇 토큰이 설정되지 않았습니다.")

    url = f"{DISCORD_API_BASE}/users/@me/guilds"
    response = requests.get(url, headers=_build_headers(bot), timeout=timeout)
    if response.status_code >= 400:
        logger.warning(
            "디스코드 길드 조회 실패 status=%s body=%s",
            response.status_code,
            response.text,
        )
        raise RuntimeError(f"디스코드 길드 조회 실패: {response.status_code}")

    payload = response.json()
    if not isinstance(payload, list):
        raise RuntimeError("디스코드 길드 조회 응답 형식이 올바르지 않습니다.")

    guild_ids: list[str] = []
    for guild in payload:
        guild_id = str(guild.get("id", "")).strip()
        if guild_id:
            guild_ids.append(guild_id)
    return guild_ids


def sync_discord_application_commands(
    bot: DiscordBot,
    *,
    timeout: int = 10,
    guild_ids: list[str] | None = None,
    sync_global: bool = True,
) -> dict:
    if not bot.application_id:
        raise ValueError("application_id가 설정되지 않았습니다.")
    if not bot.token:
        raise ValueError("봇 토큰이 설정되지 않았습니다.")

    summary = {
        "global_count": 0,
        "guild_results": [],
    }

    if sync_global:
        global_commands = _sync_global_commands(bot, timeout=timeout)
        summary["global_count"] = len(global_commands)

    if guild_ids:
        unique_guild_ids = list(dict.fromkeys([str(gid).strip() for gid in guild_ids if str(gid).strip()]))
        for guild_id in unique_guild_ids:
            guild_commands = _sync_guild_commands(bot, guild_id=guild_id, timeout=timeout)
            summary["guild_results"].append(
                {
                    "guild_id": guild_id,
                    "command_count": len(guild_commands),
                }
            )

    return summary
