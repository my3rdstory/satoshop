from django.core.management.base import BaseCommand, CommandError

from satoshop_bot.discord_commands import fetch_bot_guild_ids, sync_discord_application_commands
from satoshop_bot.models import DiscordBot


class Command(BaseCommand):
    help = "활성 디스코드 봇의 슬래시 명령어를 글로벌/길드 범위로 동기화합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--bot-id",
            type=int,
            help="특정 DiscordBot ID를 지정합니다. 미지정 시 활성 봇을 사용합니다.",
        )
        parser.add_argument(
            "--guild-id",
            action="append",
            help="길드(서버) ID를 지정합니다. 여러 번 전달 가능",
        )
        parser.add_argument(
            "--all-guilds",
            action="store_true",
            help="봇이 가입한 모든 길드에 명령어를 동기화합니다.",
        )
        parser.add_argument(
            "--global-only",
            action="store_true",
            help="글로벌 명령어만 동기화합니다.",
        )
        parser.add_argument(
            "--guild-only",
            action="store_true",
            help="길드 명령어만 동기화합니다.",
        )

    def handle(self, *args, **options):
        bot_id = options.get("bot_id")
        if bot_id:
            bot = DiscordBot.objects.filter(id=bot_id).first()
            if not bot:
                raise CommandError("지정한 DiscordBot을 찾을 수 없습니다.")
        else:
            bot = DiscordBot.get_active_bot()
            if not bot:
                raise CommandError("활성 디스코드 봇이 없습니다.")

        if not bot.application_id:
            raise CommandError("application_id가 비어 있습니다.")
        if not bot.token:
            raise CommandError("bot token이 비어 있습니다.")

        if options.get("global_only") and options.get("guild_only"):
            raise CommandError("--global-only와 --guild-only는 함께 사용할 수 없습니다.")

        sync_global = not options.get("guild_only")
        if options.get("global_only"):
            sync_global = True

        guild_ids: list[str] = []
        guild_ids.extend(options.get("guild_id") or [])

        if options.get("all_guilds"):
            discovered = fetch_bot_guild_ids(bot)
            guild_ids.extend(discovered)

        # 기본값: 글로벌 + 모든 길드 동기화(즉시 반영용)
        if not options.get("global_only") and not options.get("guild_only") and not guild_ids:
            guild_ids = fetch_bot_guild_ids(bot)

        if options.get("guild_only") and not guild_ids:
            raise CommandError("길드 전용 동기화에는 --guild-id 또는 --all-guilds가 필요합니다.")

        summary = sync_discord_application_commands(
            bot,
            guild_ids=guild_ids,
            sync_global=sync_global,
        )

        if sync_global:
            self.stdout.write(self.style.SUCCESS(f"글로벌 동기화 완료: {summary['global_count']}개"))
            self.stdout.write("  - 글로벌 명령어는 디스코드 전파에 시간이 걸릴 수 있습니다.")

        guild_results = summary.get("guild_results") or []
        if guild_results:
            self.stdout.write(self.style.SUCCESS(f"길드 동기화 완료: {len(guild_results)}개 길드"))
            for result in guild_results:
                self.stdout.write(f"  - guild {result['guild_id']}: {result['command_count']}개")
            self.stdout.write("  - 길드 명령어는 일반적으로 즉시 반영됩니다.")
