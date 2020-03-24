import base64
import requests
import urllib.parse as urlparse
from urllib.parse import parse_qs
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from . import config
from django.shortcuts import redirect
from .models import SpotifyAccount, SavedTrack


OAUTH_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
OAUTH_TOKEN_URL = "https://accounts.spotify.com/api/token"
PROFILE_INFO_URL = "https://api.spotify.com/v1/me"
AUTH_SCOPE = "user-library-read"


def get_client():
    client_id = config.get_config()['spotify_app']['client_id']
    client_secret = config.get_config()['spotify_app']['client_secret']
    spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))
    return spotify


def get_authorize_url():
    payload = {
        "client_id": config.get_config()['spotify_app']['client_id'],
        "response_type": "code",
        "redirect_uri": config.get_config()['spotify_app']['oauth_redirect_url'],
        "scope": AUTH_SCOPE,
    }
    urlparams = urlparse.urlencode(payload)
    return "%s?%s" % (OAUTH_AUTHORIZE_URL, urlparams)


def parse_response_code(url):
    params = parse_qs(urlparse.urlparse(url).query)
    return params['code']


def request_tokens(code):
    client_id = config.get_config()['spotify_app']['client_id']
    client_secret = config.get_config()['spotify_app']['client_secret']
    header = {
        "Authorization": "Basic %s" % (base64.b64encode('%s:%s' % (client_id, client_secret))) 
    }
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.get_config()['spotify_app']['oauth_redirect_url'],
    }
    print("Making request: ")
    print("Header:")
    print(header)
    print("Data:")
    print(payload)
    response = requests.post(OAUTH_TOKEN_URL, headers=headers, data=payload)
    data = response.json()
    access_token = data['access_token']
    refresh_token = data['refresh_token']
    print("Got Response:")
    print("Access Token:")
    print(access_token)
    print("Refresh Token:")
    print(refresh_token)
    return access_token, refresh_token


def authorize_user_view(request):
    return redirect(get_authorize_url())


def save_user_view(request):
    access_token = request.POST.get('access_token', None)
    refresh_token = request.POST.get('refresh_token', None)
    if access_token == None or refresh_token == None:
        return redirect('landing')
    client = spotipy.Spotify(auth=access_token)
    current_user = client.current_user()
    print(current_user)
    username = "Grayson112233"
    account = SpotifyAccount.objects.create(username=username, access_token=access_token, refresh_token=refresh_token)
