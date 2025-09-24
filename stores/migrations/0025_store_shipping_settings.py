from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0024_store_completion_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='free_shipping_threshold_krw',
            field=models.PositiveIntegerField(blank=True, help_text='원화 기준 무료 배송 조건', null=True),
        ),
        migrations.AddField(
            model_name='store',
            name='free_shipping_threshold_sats',
            field=models.PositiveIntegerField(blank=True, help_text='사토시 기준 무료 배송 조건', null=True),
        ),
        migrations.AddField(
            model_name='store',
            name='shipping_fee_krw',
            field=models.PositiveIntegerField(blank=True, help_text='원화 기준 배송비', null=True),
        ),
        migrations.AddField(
            model_name='store',
            name='shipping_fee_mode',
            field=models.CharField(choices=[('free', '무료 배송'), ('flat', '유료 고정 배송비')], default='free', help_text='스토어 배송비 정책', max_length=10),
        ),
        migrations.AddField(
            model_name='store',
            name='shipping_fee_sats',
            field=models.PositiveIntegerField(default=0, help_text='사토시 단위 고정 배송비'),
        ),
    ]
