# Generated by Django 3.0.4 on 2020-08-05 05:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('songs_in_common', '0013_merge_20200724_0309'),
    ]

    operations = [
        migrations.CreateModel(
            name='CachedCreatePlaylist',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=512)),
                ('other_username', models.CharField(max_length=512)),
            ],
        ),
    ]
