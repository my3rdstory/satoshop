# Generated by Django 5.2.2 on 2025-07-02 07:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meetup', '0006_meetuporder_attended_meetuporder_attended_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='meetuporder',
            name='auto_cancelled_reason',
            field=models.CharField(blank=True, max_length=100, verbose_name='자동 취소 사유'),
        ),
        migrations.AddField(
            model_name='meetuporder',
            name='is_temporary_reserved',
            field=models.BooleanField(default=True, verbose_name='임시 예약 상태'),
        ),
        migrations.AddField(
            model_name='meetuporder',
            name='reservation_expires_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='예약 만료 시간'),
        ),
    ]
