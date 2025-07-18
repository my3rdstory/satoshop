# Generated manually for performance optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('file', '0004_alter_digitalfile_file_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='digitalfile',
            index=models.Index(fields=['store', 'deleted_at'], name='file_store_deleted_idx'),
        ),
        migrations.AddIndex(
            model_name='digitalfile',
            index=models.Index(fields=['store', 'is_active', 'deleted_at'], name='file_store_active_idx'),
        ),
        migrations.AddIndex(
            model_name='digitalfile',
            index=models.Index(fields=['price_display'], name='file_price_display_idx'),
        ),
        migrations.AddIndex(
            model_name='digitalfile',
            index=models.Index(fields=['file_hash'], name='file_hash_idx'),
        ),
        migrations.AddIndex(
            model_name='fileorder',
            index=models.Index(fields=['payment_hash'], name='file_order_payment_idx'),
        ),
        migrations.AddIndex(
            model_name='fileorder',
            index=models.Index(fields=['digital_file', 'user', 'status'], name='file_order_composite_idx'),
        ),
    ]