# Generated by Django 5.2.2 on 2025-06-12 22:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='price_display',
            field=models.CharField(choices=[('sats', '사토시'), ('krw', '원화')], default='sats', max_length=4, verbose_name='가격 표시 방식'),
        ),
    ]
