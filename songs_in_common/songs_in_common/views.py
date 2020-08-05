from django.shortcuts import render
from . import spotify
from .models import SpotifyAccount


def landing(request):
    compare_with = request.GET.get('compare_with', None)
    compare_with_param = ""
    if compare_with:
        compare_with_param = "&compare_with=" + compare_with
    return render(request, 'songs_in_common/landing.html', {"compare_with_param": compare_with_param})


def loading(request):
    username = request.GET.get('user', "")
    return render(request, 'songs_in_common/loading.html', {"username": username})
