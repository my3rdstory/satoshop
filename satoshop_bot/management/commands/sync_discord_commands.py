from django.core.management.base import BaseCommand, CommandError

from satoshop_bot.discord_commands import sync_discord_application_commands
from satoshop_bot.models import DiscordBot


class Command(BaseCommand):
    help = "활성 디스코드 봇의 슬래시 명령어를 동기화합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--bot-id",
            type=int,
            help="특정 DiscordBot ID를 지정합니다. 미지정 시 활성 봇을 사용합니다.",
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

        commands = sync_discord_application_commands(bot)
        self.stdout.write(self.style.SUCCESS(f"동기화 완료: {len(commands)}개"))
        for command in commands:
            name = command.get("name", "")
            command_id = command.get("id", "")
            self.stdout.write(f"- {name} ({command_id})")
