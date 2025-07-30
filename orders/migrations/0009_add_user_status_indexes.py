# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0008_update_order_number_format_final'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['user', 'status'], name='orders_orde_user_id_d0bbfd_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['user', 'status', 'created_at'], name='orders_orde_user_id_8a7f3c_idx'),
        ),
    ]