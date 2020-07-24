import base64
import threading
import requests
from io import BytesIO
import urllib.parse as urlparse
from urllib.parse import parse_qs
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from fuzzywuzzy import process
from . import config
from django.core import files
from django.db import models
from django.http import HttpResponse
from django.shortcuts import render, redirect, reverse
from .models import SpotifyAccount, SavedTrack, FollowedPlaylist


OAUTH_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
OAUTH_TOKEN_URL = "https://accounts.spotify.com/api/token"
PROFILE_INFO_URL = "https://api.spotify.com/v1/me"
AUTH_SCOPE = "user-library-read"

COMPARE_WITH_CACHE = {}
PROCESSING_USERS = []


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
    headers = {
        "Authorization": "Basic %s" % (base64.b64encode(('%s:%s' % (client_id, client_secret)).encode()).decode('utf-8')), 
    }
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.get_config()['spotify_app']['oauth_redirect_url'],
    }
    response = requests.post(OAUTH_TOKEN_URL, headers=headers, data=payload)
    data = response.json()
    access_token = data['access_token']
    refresh_token = data['refresh_token']
    return access_token, refresh_token


def request_bearer_token():
    client_id = config.get_config()['spotify_app']['client_id']
    client_secret = config.get_config()['spotify_app']['client_secret']
    headers = {
        "Authorization": "Basic %s" % (base64.b64encode(('%s:%s' % (client_id, client_secret)).encode()).decode('utf-8')), 
    }
    payload = {
        "grant_type": "client_credentials"
    }
    response = requests.post(OAUTH_TOKEN_URL, headers=headers, data=payload)
    data = response.json()
    return data['access_token']


def save_saved_tracks_from_user(account):
    spotify = spotipy.Spotify(auth=account.access_token)
    tracks = []
    results = spotify.current_user_saved_tracks(limit=50)
    tracks += results['items']
    while results['next']:
        results = spotify.next(results)
        tracks += results['items']
    track_objects = []
    for track in [t['track'] for t in tracks]:
        title = track['name']
        album = track['album']['name']
        artists = ', '.join([artist['name'] for artist in track['artists']])
        uri = track['uri']
        url = track['external_urls'].get('spotify', '')
        track_objects.append(SavedTrack(user=account, title=title, album=album, artists=artists, uri=uri, url=url))
    SavedTrack.objects.bulk_create(track_objects)


# Only gets the first 50 public playlists
def get_public_playlists(account):
    token = request_bearer_token()
    spotify = spotipy.Spotify(auth=token)
    playlists = []
    results = spotify.user_playlists(account.username, limit=50)
    playlists += results['items']
    while results['next']:
        results = spotify.next(results)
        playlists += results['items']
    return playlists


def save_tracks_from_owned_playlists(account, playlists):
    token = request_bearer_token()
    spotify = spotipy.Spotify(auth=token)
    track_objects = []
    for playlist in playlists:
        if playlist['owner']['id'] == account.username:
            results = spotify.playlist(playlist['id'], fields="tracks,next")['tracks']
            track_objects += results['items']
            while results['next']:
                results = spotify.next(results)
                track_objects += results['items']
    track_db_objects = []
    for track in [t['track'] for t in track_objects]:
        title = track['name']
        album = track['album']['name']
        artists = ', '.join([artist['name'] for artist in track['artists']])
        uri = track['uri']
        url = track['external_urls'].get('spotify', '')
        track_db_objects.append(SavedTrack(user=account, title=title, album=album, artists=artists, uri=uri, url=url, from_playlist=True))
    SavedTrack.objects.bulk_create(track_db_objects)


def save_followed_playlists(account, playlists):
    playlist_objects = []
    for playlist in playlists:
        name = playlist['name']
        owner_username = playlist['owner']['id']
        owner_display_name = playlist['owner']['display_name']
        spotify_id = playlist['id']
        num_tracks = playlist['tracks']['total']
        url = playlist['external_urls'].get('spotify', '')
        playlist_objects.append(FollowedPlaylist(user=account, name=name, owner_username=owner_username, spotify_id=spotify_id, num_tracks=num_tracks, owner_display_name=owner_display_name))
    FollowedPlaylist.objects.bulk_create(playlist_objects)


def get_common_playlists(user1, user2):
    user1_playlist_ids = [pl.spotify_id for pl in FollowedPlaylist.objects.filter(user=user1)]
    user2_playlist_ids = [pl.spotify_id for pl in FollowedPlaylist.objects.filter(user=user2)]
    intersect_playlist_ids = list(set(user1_playlist_ids) & set(user2_playlist_ids))
    playlist_objects = []
    for id in intersect_playlist_ids:
        playlist_objects.append(FollowedPlaylist.objects.filter(spotify_id=id)[0])
    return playlist_objects


def save_profile_image(account):
    token = request_bearer_token()
    spotify = spotipy.Spotify(auth=token)
    spotify_user = spotify.user(account.username)
    image_url = None
    try:
        image_url = spotify_user['images'][0]['url']
    except Exception:
        return
    response = requests.get(image_url, stream=True)
    stream = BytesIO()
    stream.write(response.content)
    filename = account.username
    account.profile_image.save(filename, files.File(stream))


def save_all_profile_images():
    for account in SpotifyAccount.objects.all():
        save_profile_image(account)


def fuzzy_search_users(search_string, username):
    display_names = SpotifyAccount.objects.exclude(username=username).values_list('display_name', flat=True)
    search_names = [x[0] for x in process.extract(search_string, display_names, limit=5)]
    whens = []
    for sort_index, value in enumerate(search_names):
        whens.append(models.When(display_name=value, then=sort_index))
    query = SpotifyAccount.objects.annotate(_sort_index=models.Case(*whens, output_field=models.IntegerField()))
    return query.exclude(_sort_index=None).order_by('_sort_index')


def get_intersection_view(request):
    username1 = request.GET.get('user1')
    username2 = request.GET.get('user2')
    user1 = SpotifyAccount.objects.get(username=username1)
    user2 = SpotifyAccount.objects.get(username=username2)
    user1_uris = [track.uri for track in user1.savedtrack_set.all()]
    user2_uris = [track.uri for track in user2.savedtrack_set.all()]
    intersect_uris = list(set(user1_uris) & set(user2_uris)) 
    tracks = []
    for uri in intersect_uris:
        tracks.append(SavedTrack.objects.filter(uri=uri)[0])
    playlists = get_common_playlists(user1, user2)
    # refresh_all_public_playlists_and_playlist_saved_tracks()
    return render(request, 'songs_in_common/common.html', 
        {
            "num_tracks": len(tracks),
            "tracks": tracks,
            "user1": user1,
            "user2": user2,
            "num_playlists": len(playlists),
            "playlists": playlists,
        })


def users_view(request):
    username = request.GET.get("user", None)
    other_users = []
    if username == None:
        return redirect('landing')
    # Handle invite links (see authorize_user_view for explaination)
    global COMPARE_WITH_CACHE
    ip = str(get_client_ip(request))
    compare_with = COMPARE_WITH_CACHE.get(ip, None)
    if compare_with:
        print("COMPARE WITH TRIGGERED")
        del COMPARE_WITH_CACHE[ip]
        return redirect(reverse('common') + "?user1=" + username + "&user2=" + compare_with)
    # Search if query is provided
    search_string = request.GET.get('search', None)
    if search_string:
        other_users = fuzzy_search_users(search_string, username)
    else:
    # Default: Display me and 9 most recent users
        other_users = [SpotifyAccount.objects.get(username='grayson112233')]
        other_users += list(SpotifyAccount.objects.exclude(username=username)[:9])
    invite_link = "https://www.songsincommon.com/?compare_with=" + username
    # save_all_profile_images()
    return render(request, "songs_in_common/users.html", {"username": username, "users": other_users, "invite_link": invite_link, "search_string": search_string})


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def save_user_data(account):
    global PROCESSING_USERS
    PROCESSING_USERS.append(account.username)
    save_saved_tracks_from_user(account)
    playlists = get_public_playlists(account)
    save_tracks_from_owned_playlists(account, playlists)
    save_followed_playlists(account, playlists)
    PROCESSING_USERS.remove(account.username)


def get_status_view(request):
    username = request.GET.get('user', None)
    if username == None:
        return redirect('landing')
    if username in PROCESSING_USERS:
        return HttpResponse('Processing')
    return HttpResponse('Done')



def authorize_user_view(request):
    # When someone is given an invite link, we cannot add the query string to
    # the redirect URL during their Spotify authorization. We must instead
    # cache the user they are supposed to compare with, associated with their IP.
    compare_with = request.GET.get("compare_with", None)
    if compare_with:
        global COMPARE_WITH_CACHE
        COMPARE_WITH_CACHE[str(get_client_ip(request))] = compare_with
    return redirect(get_authorize_url())


def refresh_all_public_playlists_and_playlist_saved_tracks():
    users = SpotifyAccount.objects.all()
    for user in users:
        playlists = get_public_playlists(user)
        save_tracks_from_owned_playlists(user, playlists)
        save_followed_playlists(user, playlists)


def save_user_view(request):
    code = request.GET.get('code')
    access_token, refresh_token = request_tokens(code)
    client = spotipy.Spotify(auth=access_token)
    current_user = client.current_user()
    username = current_user['id']
    display_name = current_user['display_name']
    url = "https://open.spotify.com/user/" + username
    try:
        existing_account = SpotifyAccount.objects.get(username=username)
        existing_account.delete()
    except SpotifyAccount.DoesNotExist:
        pass
    image_url = None
    try:
        image_url = current_user['images'][0]['url']
    except Exception:
        pass
    account = SpotifyAccount.objects.create(username=username, access_token=access_token, refresh_token=refresh_token, url=url, display_name=display_name)
    save_profile_image(account)
    thread = threading.Thread(target=save_user_data, args=(account,))
    thread.start()
    return redirect(reverse('loading') + "?user=" + account.username)
