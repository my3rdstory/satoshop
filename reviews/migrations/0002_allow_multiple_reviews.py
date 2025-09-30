from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('reviews', '0001_initial'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='review',
            name='unique_review_per_product_per_author',
        ),
    ]
