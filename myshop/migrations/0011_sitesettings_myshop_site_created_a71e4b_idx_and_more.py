# Generated by Django 5.2.2 on 2025-06-17 05:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myshop', '0010_alter_sitesettings_favicon_url_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='sitesettings',
            index=models.Index(fields=['created_at'], name='myshop_site_created_a71e4b_idx'),
        ),
        migrations.AddIndex(
            model_name='sitesettings',
            index=models.Index(fields=['updated_at'], name='myshop_site_updated_86d748_idx'),
        ),
        migrations.AddIndex(
            model_name='sitesettings',
            index=models.Index(fields=['enable_user_registration'], name='myshop_site_enable__0cc87c_idx'),
        ),
        migrations.AddIndex(
            model_name='sitesettings',
            index=models.Index(fields=['enable_store_creation'], name='myshop_site_enable__9c1d21_idx'),
        ),
    ]
