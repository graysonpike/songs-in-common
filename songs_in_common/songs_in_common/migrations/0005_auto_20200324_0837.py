# Generated by Django 3.0.4 on 2020-03-24 08:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('songs_in_common', '0004_spotifyaccount_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='savedtrack',
            name='url',
            field=models.CharField(default='', max_length=512),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='savedtrack',
            name='uri',
            field=models.CharField(max_length=256),
        ),
    ]
