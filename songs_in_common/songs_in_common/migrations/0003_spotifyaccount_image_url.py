# Generated by Django 3.0.4 on 2020-03-24 05:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('songs_in_common', '0002_auto_20200324_0516'),
    ]

    operations = [
        migrations.AddField(
            model_name='spotifyaccount',
            name='image_url',
            field=models.CharField(max_length=1024, null=True),
        ),
    ]
