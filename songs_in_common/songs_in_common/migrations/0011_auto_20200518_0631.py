# Generated by Django 3.0.4 on 2020-05-18 06:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('songs_in_common', '0010_auto_20200326_0738'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='spotifyaccount',
            options={'ordering': ['-datetime_joined']},
        ),
    ]
