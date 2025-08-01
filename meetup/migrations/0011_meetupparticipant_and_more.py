# Generated by Django 5.2.2 on 2025-07-03 06:05

import django.contrib.auth.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('meetup', '0010_delete_pendingordermanager'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MeetupParticipant',
            fields=[
            ],
            options={
                'verbose_name': '밋업 참가자',
                'verbose_name_plural': '밋업 참가자 목록',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('auth.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.AddIndex(
            model_name='meetuporder',
            index=models.Index(fields=['status', 'user'], name='meetup_meet_status_b752ef_idx'),
        ),
        migrations.AddIndex(
            model_name='meetuporder',
            index=models.Index(fields=['user', 'created_at'], name='meetup_meet_user_id_9fd339_idx'),
        ),
        migrations.AddIndex(
            model_name='meetuporder',
            index=models.Index(fields=['status', 'created_at'], name='meetup_meet_status_cbac46_idx'),
        ),
        migrations.AddIndex(
            model_name='meetuporder',
            index=models.Index(fields=['user', 'status', 'created_at'], name='meetup_meet_user_id_9f79a7_idx'),
        ),
        migrations.AddIndex(
            model_name='meetuporder',
            index=models.Index(fields=['is_temporary_reserved'], name='meetup_meet_is_temp_0f4b88_idx'),
        ),
        migrations.AddIndex(
            model_name='meetuporder',
            index=models.Index(fields=['attended'], name='meetup_meet_attende_880ecd_idx'),
        ),
        migrations.AddIndex(
            model_name='meetuporder',
            index=models.Index(fields=['reservation_expires_at'], name='meetup_meet_reserva_a54d73_idx'),
        ),
        migrations.AddIndex(
            model_name='meetuporder',
            index=models.Index(fields=['paid_at'], name='meetup_meet_paid_at_e35cdd_idx'),
        ),
        migrations.AddIndex(
            model_name='meetuporder',
            index=models.Index(fields=['confirmed_at'], name='meetup_meet_confirm_53b332_idx'),
        ),
        migrations.AddIndex(
            model_name='meetuporder',
            index=models.Index(fields=['attended_at'], name='meetup_meet_attende_2c2b71_idx'),
        ),
        migrations.AddIndex(
            model_name='meetuporder',
            index=models.Index(fields=['user', 'total_price'], name='meetup_meet_user_id_abdcd4_idx'),
        ),
        migrations.AddIndex(
            model_name='meetuporder',
            index=models.Index(fields=['meetup', 'user'], name='meetup_meet_meetup__e87843_idx'),
        ),
    ]
