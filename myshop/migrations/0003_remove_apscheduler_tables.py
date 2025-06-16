# Generated manually to remove Django APScheduler tables

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('myshop', '0002_exchangerate_and_more'),
    ]

    operations = [
        # Django APScheduler 테이블 삭제 (존재하는 경우에만)
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS django_apscheduler_djangojob CASCADE;",
            reverse_sql="-- 복원할 수 없음",
        ),
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS django_apscheduler_djangojobexecution CASCADE;",
            reverse_sql="-- 복원할 수 없음",
        ),
    ] 