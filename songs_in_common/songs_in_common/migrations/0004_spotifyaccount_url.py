# Generated by Django 3.0.4 on 2020-03-24 07:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('songs_in_common', '0003_spotifyaccount_image_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='spotifyaccount',
            name='url',
            field=models.CharField(default='#', max_length=1024),
            preserve_default=False,
        ),
    ]
