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
from django.contrib.auth.decorators import user_passes_test
from .models import SpotifyAccount, SavedTrack, FollowedPlaylist, ProcessingUser, CachedCompareWith, CachedCreatePlaylist


OAUTH_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
OAUTH_TOKEN_URL = "https://accounts.spotify.com/api/token"
PROFILE_INFO_URL = "https://api.spotify.com/v1/me"
AUTH_SCOPE = "user-library-read playlist-modify-public playlist-read-private playlist-read-collaborative"


def get_authorize_url(action):
    payload = {
        "client_id": config.get_config()['spotify_app']['client_id'],
        "response_type": "code",
        "redirect_uri": config.get_config()['spotify_app']['oauth_redirect_urls'][action],
        "scope": AUTH_SCOPE,
    }
    urlparams = urlparse.urlencode(payload)
    return "%s?%s" % (OAUTH_AUTHORIZE_URL, urlparams)


def parse_response_code(url):
    params = parse_qs(urlparse.urlparse(url).query)
    return params['code']


def request_tokens(code, action):
    client_id = config.get_config()['spotify_app']['client_id']
    client_secret = config.get_config()['spotify_app']['client_secret']
    headers = {
        "Authorization": "Basic %s" % (base64.b64encode(('%s:%s' % (client_id, client_secret)).encode()).decode('utf-8')), 
    }
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.get_config()['spotify_app']['oauth_redirect_urls'][action],
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


# Only gets the first 50 playlists
def get_playlists(account):
    token = request_bearer_token()
    spotify = spotipy.Spotify(auth=account.access_token)
    playlists = []
    results = spotify.current_user_playlists(limit=50)
    playlists += results['items']
    while results['next']:
        results = spotify.next(results)
        playlists += results['items']
    return playlists


def create_playlist(client, name):
    user_id = client.current_user()['id']
    return client.user_playlist_create(user_id, name, description="Created with SongsInCommon.com")


def divide_chunks(l, n):  
    for i in range(0, len(l), n):  
        yield l[i:i + n]


def add_tracks_to_playlist(client, playlist_id, tracks):
    user_id = client.current_user()['id']
    # Break track uri list into groups of 100 tracks or less
    uri_groups = divide_chunks(tracks, 100)
    for uri_group in uri_groups:
        print(client.user_playlist_add_tracks(user_id, playlist_id, uri_group))


def create_common_playlist_view(request):
    code = request.GET.get('code', None)
    if code == None:
        username = request.GET.get('user', None)
        other_username = request.GET.get('other', None)
        if username == None or other_username == None:
            return redirect('landing')
        CachedCreatePlaylist.objects.create(username=username, other_username=other_username)
        return redirect("/authorize?action=create_playlist")
    access_token, refresh_token = request_tokens(code, 'create_playlist')
    client = spotipy.Spotify(auth=access_token)
    spotipy_user = client.current_user()
    username = spotipy_user['id']
    cached_object = CachedCreatePlaylist.objects.get(username=username)
    other_username = cached_object.other_username
    cached_object.delete()
    account = SpotifyAccount.objects.get(username=username)
    other_account = SpotifyAccount.objects.get(username=other_username)
    common_tracks_uris = get_tracks_intersection_uris(account, other_account)
    playlist = create_playlist(client, "Songs in Common with %s" % (other_account.display_name))
    add_tracks_to_playlist(client, playlist['id'], common_tracks_uris)
    return redirect('/playlist-created?user=%s&other=%s&plid=%s' % (username, other_username, playlist['id']))


def playlist_created_view(request):
    username = request.GET.get('user')
    other_username = request.GET.get('other')
    account = SpotifyAccount.objects.get(username=username)
    other_account = SpotifyAccount.objects.get(username=other_username)
    token = request_bearer_token()
    client = spotipy.Spotify(auth=token)
    playlist = client.playlist(request.GET.get('plid'))

    return render(request, 'songs_in_common/playlist_created.html', 
        {
            "user1": account,
            "user2": other_account,
            "playlist_url": playlist['external_urls'].get('spotify', '')
        })


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


def get_tracks_intersection_uris(account1, account2):
    account1_uris = [track.uri for track in account1.savedtrack_set.all()]
    account2_uris = [track.uri for track in account2.savedtrack_set.all()]
    return list(set(account1_uris) & set(account2_uris))


def get_intersection_view(request):
    username1 = request.GET.get('user1')
    username2 = request.GET.get('user2')
    account1 = SpotifyAccount.objects.get(username=username1)
    account2 = SpotifyAccount.objects.get(username=username2)
    intersect_uris = get_tracks_intersection_uris(account1, account2)
    tracks = []
    for uri in intersect_uris:
        tracks.append(SavedTrack.objects.filter(uri=uri)[0])
    playlists = get_common_playlists(account1, account2)
    return render(request, 'songs_in_common/common.html', 
        {
            "num_tracks": len(tracks),
            "tracks": tracks,
            "user1": account1,
            "user2": account2,
            "num_playlists": len(playlists),
            "playlists": playlists,
        })


def get_client_ip(request):
    return request.META.get('HTTP_X_REAL_IP')


def users_view(request):
    username = request.GET.get("user", None)
    other_users = []
    if username == None:
        return redirect('landing')
    # Handle invite links (see authorize_user_view for explaination)
    ip = str(get_client_ip(request))
    try:
        cache_entry = CachedCompareWith.objects.get(ip=ip)
        compare_with = cache_entry.username
        cache_entry.delete()
        return redirect(reverse('common') + "?user1=" + username + "&user2=" + compare_with)
    except CachedCompareWith.DoesNotExist: pass
    # Search if query is provided
    search_string = request.GET.get('search', None)
    if search_string:
        other_users = fuzzy_search_users(search_string, username)
    else:
    # Default: Display me and 9 most recent users
        other_users = [SpotifyAccount.objects.get(username='grayson112233')]
        other_users += list(SpotifyAccount.objects.exclude(username=username).exclude(username='grayson112233')[:9])
    invite_link = "https://www.songsincommon.com/?compare_with=" + username
    # save_all_profile_images()
    return render(request, "songs_in_common/users.html", {"username": username, "users": other_users, "invite_link": invite_link, "search_string": search_string})


def save_user_data(account):
    print("############################################################")
    if not ProcessingUser.objects.filter(username=account.username).exists():
        processing_user = ProcessingUser.objects.create(username=account.username)
        print("Saving user tracks")
        save_saved_tracks_from_user(account)
        print("Saving user playlists")
        playlists = get_playlists(account)
    print("save_tracks_from_owned_playlists")
    save_tracks_from_owned_playlists(account, playlists)
    print("save_followed_playlists")
    save_followed_playlists(account, playlists)
    print("Deleing processing user record")
    processing_user.delete()


def get_status_view(request):
    username = request.GET.get('user', None)
    if username == None:
        return redirect('landing')
    try:
        ProcessingUser.objects.get(username=username)
    except ProcessingUser.DoesNotExist:
        return HttpResponse('Done')
    return HttpResponse('Processing')


def authorize_user_view(request):
    # When someone is given an invite link, we cannot add the query string to
    # the redirect URL during their Spotify authorization. We must instead
    # cache the user they are supposed to compare with, associated with their IP.
    action = request.GET.get("action", None).replace("/", "")
    if action == None:
        return redirect('landing')
    if action == 'save_user':
        compare_with = request.GET.get("compare_with", None)
        if compare_with:
            ip = str(get_client_ip(request))
            CachedCompareWith.objects.create(ip=ip, username=compare_with)
    return redirect(get_authorize_url(action))


def save_user_view(request):
    code = request.GET.get('code')
    access_token, refresh_token = request_tokens(code, 'save_user')
    client = spotipy.Spotify(auth=access_token)
    current_user = client.current_user()
    username = current_user['id']
    if ProcessingUser.objects.filter(username=username).exists():
        return redirect(reverse('loading') + "?user=" + username)
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


@user_passes_test(lambda u:u.is_staff, login_url="admin/")  
def delete_processing_users_view(request):
    ProcessingUser.objects.all().delete()
    return redirect(reverse('landing'))
