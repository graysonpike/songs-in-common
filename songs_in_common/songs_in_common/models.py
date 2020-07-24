from django.db import models


class SpotifyAccount(models.Model):
    username = models.CharField(max_length=512)
    display_name = models.CharField(max_length=512)
    access_token = models.CharField(max_length=1024)
    refresh_token = models.CharField(max_length=1024)
    url = models.CharField(max_length=1024)
    profile_image = models.ImageField(upload_to='profile_images', null=True)
    datetime_joined = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-datetime_joined']


class SavedTrack(models.Model):
    user = models.ForeignKey(SpotifyAccount, on_delete=models.CASCADE)
    title = models.CharField(max_length=1024)
    album = models.CharField(max_length=1024)
    artists = models.CharField(max_length=1024)
    uri = models.CharField(max_length=256)
    url = models.CharField(max_length=512)
    from_playlist = models.BooleanField(default=False)


class FollowedPlaylist(models.Model):
    user = models.ForeignKey(SpotifyAccount, on_delete=models.CASCADE)
    name = models.CharField(max_length=1024)
    owner_username = models.CharField(max_length=512)
    owner_display_name = models.CharField(max_length=512)
    spotify_id = models.CharField(max_length=512)
    num_tracks = models.IntegerField()
    url = models.CharField(max_length=512)


class ProcessingUser(models.Model):
    username = models.CharField(max_length=1024)


class CachedCompareWith(models.Model):
    ip = models.CharField(max_length=512)
    username = models.CharField(max_length=1024)
