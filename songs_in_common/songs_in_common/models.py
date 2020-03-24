from django.db import models


class SpotifyAccount(models.Model):
    username = models.CharField(max_length=512)
    display_name = models.CharField(max_length=512)
    access_token = models.CharField(max_length=1024)
    refresh_token = models.CharField(max_length=1024)
    url = models.CharField(max_length=1024)
    image_url = models.CharField(max_length=1024, null=True)
    datetime_joined = models.DateTimeField(auto_now_add=True)


class SavedTrack(models.Model):
    user = models.ForeignKey(SpotifyAccount, on_delete=models.CASCADE)
    title = models.CharField(max_length=1024)
    album = models.CharField(max_length=1024)
    artists = models.CharField(max_length=1024)
    uri = models.CharField(max_length=256)
    url = models.CharField(max_length=512)
