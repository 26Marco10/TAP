import shutil
from dotenv import load_dotenv
import os
import base64
import requests
import json
from pytubefix import YouTube
from youtubesearchpython import VideosSearch
from flask import Flask, request, redirect, send_file, render_template
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth
from datetime import datetime
from flask import jsonify
import urllib.parse
from urllib.parse import quote
import lyricsgenius
import html
import os
from concurrent.futures import ThreadPoolExecutor
import logstash
import logging

load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
genius_token = os.getenv("GENIUS_API_TOKEN")

host = 'localhost'
port = 5959
test_logger = logging.getLogger('logstash')
test_logger.setLevel(logging.INFO)
test_logger.addHandler(logstash.TCPLogstashHandler(host, port, version=1))
test_logger.info('My test logstash message, with extra data', extra={'test_string': 'test', 'test_int': 1})

app = Flask(__name__)



executor = ThreadPoolExecutor(max_workers=10)  # Puoi modificare il numero di worker secondo le tue necessità


def get_token(code):
    auth_string = client_id + ":" + client_secret
    auth_bytes = auth_string.encode('utf-8')
    auth_base64 = str(base64.b64encode(auth_bytes),"utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "client_credentials",
        "code": code,
        "redirect_uri": "http://localhost:8000/"
    }

    result = requests.post(url, headers=headers, data=data)
    json_result = json.loads(result.content)
    token = json_result["access_token"]
    return token

def get_auth_header(token):
    return {
        "Authorization": "Bearer " + token
    }

def search_for_artist(token, artist_name):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)
    params = {
        "q": artist_name,
        "type": "artist",
        "limit": "12"
    }

    result = requests.get(url, headers=headers, params=params)
    json_result = json.loads(result.content)["artists"]["items"]
    
    if len(json_result) == 0:
        print("No artist found")
        return None
    
    return json_result

def get_favorite_songs(token, offset):
    url = "https://api.spotify.com/v1/me/tracks"
    headers = get_auth_header(token)
    params = {
        "limit": "50",
        "offset": offset
    }

    result = requests.get(url, headers=headers, params=params)
    json_result = json.loads(result.content)["items"]
    return json_result

def search_for_playlist(token, playlist_name):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)
    params = {
        "q": playlist_name,
        "type": "playlist",
        "limit": "12"
    }

    result = requests.get(url, headers=headers, params=params)
    json_result = json.loads(result.content)["playlists"]["items"]
    
    if len(json_result) == 0:
        print("No album found")
        return None
    
    return json_result

def search_for_album(token, album_name):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)
    params = {
        "q": album_name,
        "type": "album",
        "limit": "12"
    }

    result = requests.get(url, headers=headers, params=params)
    json_result = json.loads(result.content)["albums"]["items"]
    
    if len(json_result) == 0:
        print("No album found")
        return None
    
    return json_result

def search_for_song(token, song_name):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)
    params = {
        "q": song_name,
        "type": "track",
        "limit": "10"
    }

    result = requests.get(url, headers=headers, params=params)
    json_result = json.loads(result.content)["tracks"]["items"]
    
    if len(json_result) == 0:
        print("No song found")
        return None
    
    return json_result

def get_playlist_songs(token, playlist_id):
    url = "https://api.spotify.com/v1/playlists/" + playlist_id + "/tracks"
    headers = get_auth_header(token)
    params = {
        "limit": "100"
    }

    result = requests.get(url, headers=headers, params=params)
    json_result = json.loads(result.content)["items"]
    return json_result

def get_artist_albums(token, artist_id):
    url = "https://api.spotify.com/v1/artists/" + artist_id + "/albums"
    headers = get_auth_header(token)
    params = {
        "limit": "50"
    }

    result = requests.get(url, headers=headers, params=params)
    json_result = json.loads(result.content)["items"]
    return json_result

def get_album_songs(token, album_id):
    url = "https://api.spotify.com/v1/albums/" + album_id + "/tracks"
    headers = get_auth_header(token)
    params = {
        "limit": "50"
    }

    result = requests.get(url, headers=headers, params=params)
    json_result = json.loads(result.content)["items"]
    return json_result

def get_futured_playlists(token):
    url = "https://api.spotify.com/v1/browse/featured-playlists"
    headers = get_auth_header(token)
    params = {
        "limit": "100"
    }
    result = requests.get(url, headers=headers, params=params)
    json_result = json.loads(result.content)["playlists"]["items"]
    return json_result

def get_songs_by_artist(token, artist_id, country="IT"):
    url = "https://api.spotify.com/v1/artists/" + artist_id + "/top-tracks"
    headers = get_auth_header(token)
    params = {
        "market": country
    }

    result = requests.get(url, headers=headers, params=params)
    json_result = json.loads(result.content)["tracks"]
    return json_result

def get_lyrics(song_name, artist_name):
    genius = lyricsgenius.Genius(genius_token)
    #se dentro song_name ci sono delle parentesi quadre e/o tonde, prendi solo il testo prima di queste
    if "[" in song_name:
        song_name = song_name[:song_name.index("[")]
    if "(" in song_name:
        song_name = song_name[:song_name.index("(")]
    
    song = genius.search_song(song_name, artist_name)
    if song:
        lyrics = song.lyrics
        #togli la prima riga di lyrics
        lyrics = lyrics[lyrics.index("\n")+1:]
        return lyrics
    else:
        return "Lyrics not found"
    
def check_internet_connection():
    try:
        requests.get("http://www.google.com")  
        return True
    except requests.ConnectionError:
        return False

def YoutubeAudioDownload(video_url, save_path, song_name, artist_name):
    try:
        video = YouTube(video_url)
        title = song_name + " - " + artist_name
        output = video.streams.get_audio_only()
        out_file = output.download(filename=f"{title}.mp3", output_path=save_path)
        print("Audio was downloaded successfully")
        return out_file
    except Exception as e:
        print("Failed to download audio:", str(e))
        return None

def find_song_on_youtube(song_name):
    try:
        videos_search = VideosSearch(song_name, limit=1)
        link = videos_search.result()['result'][0]['link']
        return link
    except Exception as e:
        print("Failed to find song on YouTube:", str(e))
        return None

def delete_double_songs_from_favorite(token):
    songs = get_favorite_songs(token, 0)
    for i in range(50, 1000, 50):
        songs += get_favorite_songs(token, i)
    songs_id = []
    for song in songs:
        #se la canzone è già stata aggiunta controllando nome e artista, la elimina
        for song1 in songs:
            if song["track"]["name"] == song1["track"]["name"] and song["track"]["artists"][0]["name"] == song1["track"]["artists"][0]["name"] and song != song1:
                songs_id.append(song["track"]["id"])
                break
    for song_id in songs_id:
        delete_song_from_favorite(token, song_id)

def delete_song_from_favorite(token, song_id):
    url = "https://api.spotify.com/v1/me/tracks"
    headers = get_auth_header(token)
    params = {
        "ids": song_id
    }

    result = requests.delete(url, headers=headers, params=params)
    return result

def delivery_report(err, msg):
    if err is not None:
        print('Message delivery failed: {}'.format(err))
    else:
        print('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))

def produce_song_global_top(canzoni):
    print("Producing songs...")
    for song in canzoni:
        lyrics = get_lyrics(song["track"]["name"], song["track"]["artists"][0]["name"])
        name = song["track"]["name"]
        artist = song["track"]["artists"][0]["name"]
        song_id = song["track"]["id"]
        canzone = {
            "name": name,
            "artist": artist,
            "lyrics": lyrics,
            "id": song_id
        }
        string_canzone = json.dumps(canzone)
        test_logger.info(string_canzone)



AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
REDIRECT_URI = 'http://localhost:8000/callback' 
SCOPE = [
    "user-read-private user-library-modify  user-library-read user-read-email playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative"
]

session = {}

@app.route("/")
def login():
    if check_internet_connection():
        spotify = OAuth2Session(client_id, scope=SCOPE, redirect_uri=REDIRECT_URI)
        authorization_url, state = spotify.authorization_url(AUTH_URL)
        return redirect(authorization_url)
    else:
        return redirect("/local")

@app.route("/callback", methods=['GET'])
def callback():
    code = request.args.get('code')
    res = requests.post(TOKEN_URL,
        auth=HTTPBasicAuth(client_id, client_secret),
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI
        })
    session["token"] = res.json()["access_token"]
    session["refresh_token"] = res.json()["refresh_token"]
    session["expires_at"] = datetime.now().timestamp() + res.json()["expires_in"]
    date = datetime.fromtimestamp(session["expires_at"])
    print("Token: " + session["token"])
    print("Scade il " + date.strftime("%d/%m/%Y, %H:%M:%S"))
    return redirect("/index")

@app.route("/refresh")
def refresh():
    if "refresh_token" not in session:
        return redirect("/")
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': session["refresh_token"],
        'client_id': client_id,
        'client_secret': client_secret
    }
    res = requests.post(TOKEN_URL, data=data)
    session["token"] = res.json()["access_token"]
    session["expires_at"] = datetime.now().timestamp() + res.json()["expires_in"]

    return redirect("/index")

@app.route("/index")
def index():
    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")
    
    top_global = search_for_playlist(session["token"], "Top Global 50")[0]
    top_global_songs = get_playlist_songs(session["token"], top_global["id"])
    executor.submit(produce_song_global_top, top_global_songs)
    
    return jsonify(top_global_songs)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
