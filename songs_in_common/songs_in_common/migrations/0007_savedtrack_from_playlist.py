# Generated by Django 3.0.4 on 2020-03-26 01:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('songs_in_common', '0006_spotifyaccount_display_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='savedtrack',
            name='from_playlist',
            field=models.BooleanField(default=False),
        ),
    ]
