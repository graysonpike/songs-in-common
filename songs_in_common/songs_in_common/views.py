from django.shortcuts import render
from . import spotify
from .models import SpotifyAccount


def landing(request):
    return render(request, 'songs_in_common/landing.html')
