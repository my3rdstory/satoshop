from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lecture", "0005_livelectureorder_lecture_liv_live_le_0f102e_idx"),
        ("ln_payment", "0002_paymenttransaction_meetup_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymenttransaction",
            name="live_lecture_order",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="payment_transactions",
                to="lecture.livelectureorder",
                verbose_name="연결 라이브 강의 주문",
            ),
        ),
    ]
