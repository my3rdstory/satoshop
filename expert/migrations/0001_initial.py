import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Contract',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('title', models.CharField(max_length=150)),
                ('status', models.CharField(choices=[('draft', '작성 중'), ('pending_counterparty', '상대방 확인 대기'), ('awaiting_signature', '서명 대기'), ('signed', '서명 완료'), ('payment_pending', '지급 진행 중'), ('completed', '완료'), ('cancelled', '취소')], default='draft', max_length=32)),
                ('chat_archive', models.FileField(blank=True, help_text='채팅 기록을 PDF로 저장한 파일', null=True, upload_to='contracts/chat_archives/')),
                ('archive_generated_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='contracts_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ContractParticipant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('client', '의뢰자'), ('performer', '수행자')], max_length=16)),
                ('lightning_identifier', models.CharField(help_text='라이트닝 인증 결과(아이디 등)를 저장', max_length=128)),
                ('is_confirmed', models.BooleanField(default=False)),
                ('signed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('contract', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participants', to='expert.contract')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='expert_contract_participations', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ContractMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sender_role', models.CharField(blank=True, choices=[('client', '의뢰자'), ('performer', '수행자')], max_length=16)),
                ('message_type', models.CharField(choices=[('text', '텍스트'), ('system', '시스템')], default='text', max_length=16)),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('contract', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='expert.contract')),
                ('sender', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='contract_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='contractparticipant',
            constraint=models.UniqueConstraint(fields=('contract', 'user'), name='unique_contract_participant'),
        ),
        migrations.CreateModel(
            name='ContractEmailLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipients', models.TextField(help_text='쉼표로 구분된 수신자 이메일')),
                ('subject', models.CharField(max_length=140)),
                ('message', models.TextField()),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('success', models.BooleanField(default=True)),
                ('error_message', models.TextField(blank=True)),
                ('contract', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='email_logs', to='expert.contract')),
            ],
            options={
                'ordering': ['-sent_at'],
            },
        ),
    ]
