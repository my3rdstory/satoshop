# Generated manually for browse stores page optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('file', '0005_add_performance_indexes'),
    ]

    operations = [
        # FileOrder 모델에 브라우즈 페이지용 인덱스 추가
        migrations.AddIndex(
            model_name='fileorder',
            index=models.Index(fields=['status', 'confirmed_at'], name='file_order_browse_idx'),
        ),
        migrations.AddIndex(
            model_name='fileorder',
            index=models.Index(fields=['confirmed_at'], name='file_order_confirmed_idx'),
        ),
    ]