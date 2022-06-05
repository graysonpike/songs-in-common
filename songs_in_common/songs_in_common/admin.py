from django.contrib import admin
from . import models


admin.site.register(models.ProcessingUser)
admin.site.register(models.SpotifyAccount)
admin.site.register(models.CachedCompareWith)
admin.site.register(models.CachedCreatePlaylist)
