from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0009_product_is_temporarily_out_of_stock'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='force_free_shipping',
            field=models.BooleanField(
                default=False,
                help_text='체크 시 스토어 기본 배송비를 무시하고 무료 배송으로 계산',
                verbose_name='무조건 무료 배송',
            ),
        ),
    ]
