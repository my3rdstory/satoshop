"""개발 서버 기본 포트를 8011로 고정하기 위한 runserver 커맨드 오버라이드."""

from django.core.management.commands.runserver import Command as DjangoRunserverCommand


class Command(DjangoRunserverCommand):
    """기본 runserver 커맨드를 확장해 개발 기본 포트를 변경."""

    default_port = '8011'
