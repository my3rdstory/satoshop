# Generated by Django 5.2.2 on 2025-07-08 23:44

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lecture', '0002_livelecture_livelectureimage_livelectureorder_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='livelectureorder',
            constraint=models.UniqueConstraint(condition=models.Q(('status__in', ['confirmed', 'completed'])), fields=('live_lecture', 'user'), name='unique_active_live_lecture_order_per_user'),
        ),
    ]
