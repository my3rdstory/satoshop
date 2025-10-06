from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0030_bahpromotionlinksettings_package_request_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='bahpromotionlinksettings',
            name='email_store_id',
            field=models.CharField(
                blank=True,
                default='',
                help_text='이메일 설정 스토어 아이디: 입력된 스토어의 이메일 발송 설정을 사용해 홍보요청 내용을 메일로 전송합니다.',
                max_length=50,
            ),
        ),
        migrations.RemoveField(
            model_name='bahpromotionlinksettings',
            name='package_request_url',
        ),
    ]
