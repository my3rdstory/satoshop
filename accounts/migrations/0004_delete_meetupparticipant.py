# Generated by Django 5.2.2 on 2025-07-03 12:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_meetupparticipant'),
    ]

    operations = [
        migrations.DeleteModel(
            name='MeetupParticipant',
        ),
    ]
