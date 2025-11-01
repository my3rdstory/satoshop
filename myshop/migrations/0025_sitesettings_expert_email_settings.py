from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myshop', '0024_sitesettings_superuser_checkout_address_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='expert_email_sender_name',
            field=models.CharField(blank=True, help_text='수신자에게 표시될 발신자 명칭 (미입력 시 Gmail 주소가 사용됩니다).', max_length=120, verbose_name='Expert 이메일 발신자 이름'),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='expert_gmail_address',
            field=models.EmailField(blank=True, help_text='자동 계약 이메일에 사용할 Gmail 주소를 입력하세요. 2단계 인증을 활성화하고 앱 비밀번호를 발급받아야 합니다.', max_length=254, verbose_name='Expert 계약 이메일 발송 Gmail 주소'),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='expert_gmail_app_password',
            field=models.CharField(blank=True, help_text='Google 계정 보안 설정에서 생성한 16자리 앱 비밀번호를 입력하세요. (예: abcd efgh ijkl mnop)', max_length=128, verbose_name='Gmail 앱 비밀번호'),
        ),
    ]
