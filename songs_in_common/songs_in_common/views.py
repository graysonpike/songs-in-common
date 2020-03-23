from django.shortcuts import render


def landing(request):
    return render(request, 'songs_in_common/landing.html')
