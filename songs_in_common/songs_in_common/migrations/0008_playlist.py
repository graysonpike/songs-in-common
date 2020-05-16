# Generated by Django 3.0.4 on 2020-03-26 03:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('songs_in_common', '0007_savedtrack_from_playlist'),
    ]

    operations = [
        migrations.CreateModel(
            name='Playlist',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=1024)),
                ('owner_username', models.CharField(max_length=512)),
                ('spotify_id', models.CharField(max_length=512)),
                ('num_tracks', models.IntegerField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='songs_in_common.SpotifyAccount')),
            ],
        ),
    ]