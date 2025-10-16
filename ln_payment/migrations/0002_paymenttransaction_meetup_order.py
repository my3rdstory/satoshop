from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("meetup", "0017_meetup_meetup_meet_is_free_ed72b4_idx_and_more"),
        ("ln_payment", "0002_manualpaymenttransaction"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymenttransaction",
            name="meetup_order",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="payment_transactions",
                to="meetup.meetuporder",
                verbose_name="연결 밋업 주문",
            ),
        ),
    ]
