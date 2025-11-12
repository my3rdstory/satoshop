from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("expert", "0008_alter_directcontractdocument_counterparty_signature_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="directcontractdocument",
            name="payment_meta",
            field=models.JSONField(blank=True, default=dict, help_text="단계별 라이트닝 결제 정보"),
        ),
    ]
