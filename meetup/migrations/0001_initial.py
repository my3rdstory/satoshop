# Generated by Django 5.2.2 on 2025-06-30 08:29

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('stores', '0023_add_email_settings'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Meetup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='밋업명')),
                ('description', models.TextField(blank=True, verbose_name='설명')),
                ('price', models.PositiveIntegerField(default=0, verbose_name='참가비(satoshi)')),
                ('is_discounted', models.BooleanField(default=False, verbose_name='할인 적용')),
                ('discounted_price', models.PositiveIntegerField(blank=True, null=True, verbose_name='할인가(satoshi)')),
                ('early_bird_end_date', models.DateField(blank=True, null=True, verbose_name='조기등록 종료일')),
                ('early_bird_end_time', models.TimeField(blank=True, null=True, verbose_name='조기등록 종료시간')),
                ('is_active', models.BooleanField(default=True, verbose_name='활성화')),
                ('is_temporarily_closed', models.BooleanField(default=False, verbose_name='일시중단')),
                ('max_participants', models.PositiveIntegerField(blank=True, null=True, verbose_name='최대 참가자')),
                ('completion_message', models.TextField(blank=True, verbose_name='참가완료 안내메시지')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='meetups', to='stores.store')),
            ],
            options={
                'verbose_name': '밋업',
                'verbose_name_plural': '밋업',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MeetupOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='옵션명')),
                ('is_required', models.BooleanField(default=False, verbose_name='필수 선택')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='정렬순서')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('meetup', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='options', to='meetup.meetup')),
            ],
            options={
                'verbose_name': '밋업 옵션',
                'verbose_name_plural': '밋업 옵션',
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='MeetupChoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='선택지명')),
                ('additional_price', models.IntegerField(default=0, verbose_name='추가요금(satoshi)')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='정렬순서')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('option', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='choices', to='meetup.meetupoption')),
            ],
            options={
                'verbose_name': '밋업 선택지',
                'verbose_name_plural': '밋업 선택지',
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='MeetupImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_name', models.CharField(max_length=255, verbose_name='원본 파일명')),
                ('file_path', models.CharField(max_length=500, verbose_name='파일 경로')),
                ('file_url', models.URLField(max_length=800, verbose_name='파일 URL')),
                ('file_size', models.PositiveIntegerField(blank=True, null=True, verbose_name='파일 크기 (bytes)')),
                ('width', models.PositiveIntegerField(default=500, verbose_name='이미지 너비')),
                ('height', models.PositiveIntegerField(default=500, verbose_name='이미지 높이')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='정렬 순서')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='업로드 시간')),
                ('meetup', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='meetup.meetup')),
                ('uploaded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='업로드 사용자')),
            ],
            options={
                'verbose_name': '밋업 이미지',
                'verbose_name_plural': '밋업 이미지들',
                'ordering': ['order', 'uploaded_at'],
                'indexes': [models.Index(fields=['meetup', 'order'], name='meetup_meet_meetup__c78b69_idx'), models.Index(fields=['uploaded_at'], name='meetup_meet_uploade_a468b5_idx')],
            },
        ),
    ]
