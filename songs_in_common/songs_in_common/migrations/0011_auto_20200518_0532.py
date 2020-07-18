# Generated by Django 3.0.4 on 2020-05-18 05:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('songs_in_common', '0010_auto_20200326_0738'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='spotifyaccount',
            options={'ordering': ['-datetime_joined']},
        ),
        migrations.RemoveField(
            model_name='spotifyaccount',
            name='image_url',
        ),
        migrations.AddField(
            model_name='spotifyaccount',
            name='profile_image',
            field=models.ImageField(null=True, upload_to='profile_images'),
            preserve_default=False,
        ),
    ]