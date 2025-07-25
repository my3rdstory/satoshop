# Generated by Django 5.2.2 on 2025-06-11 22:25

import django.core.validators
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0014_change_owner_to_fk'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='store',
            name='store_id',
            field=models.CharField(help_text='스토어 접속 경로로 사용됩니다. (예: mystore)', max_length=50, validators=[django.core.validators.RegexValidator(message='스토어 아이디는 영문, 숫자, 하이픈(-), 언더스코어(_)만 사용 가능합니다.', regex='^[a-zA-Z0-9_-]+$')]),
        ),
        migrations.AddConstraint(
            model_name='store',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted_at__isnull', True)), fields=('store_id',), name='unique_active_store_id'),
        ),
    ]
