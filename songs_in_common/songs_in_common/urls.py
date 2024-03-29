from . import views, spotify


"""songs_in_common URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.landing, name='landing'),
    path('authorize/', spotify.authorize_user_view, name='authorize'),
    path('save-user/', spotify.save_user_view, name='save_user'),
    path('common/', spotify.get_intersection_view, name='common'),
    path('users/', spotify.users_view, name='users'),
    path('loading/', views.loading, name='loading'),
    path('get-status/', spotify.get_status_view, name='get_status'),
    path('create-playlist/', spotify.create_common_playlist_view, name='create_playlist'),
    path('playlist-created/', spotify.playlist_created_view, name='playlist_created'),
    path('delete-processing-users/', spotify.delete_processing_users_view, name='delete_processing_users')
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
