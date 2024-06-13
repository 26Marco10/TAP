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
import logging
import logstash

# Set up Logstash
host = 'logstash'
port = 5959
test_logger = logging.getLogger('logstash')
test_logger.setLevel(logging.INFO)
test_logger.addHandler(logstash.TCPLogstashHandler(host, port, version=1))

load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
genius_token = os.getenv("GENIUS_API_TOKEN")

global max_offset_for_favorites

app = Flask(__name__)

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
    song_name = song_name.split('[')[0].split('(')[0].strip()
    try:
        song = genius.search_song(song_name, artist_name)
    except Exception as e:
        print(f"Error: {e}")
        return "Lyrics not found"
        
    if song:
        # se lyrics contiene [FN# allora ritorna Lyrics not found
        if song.lyrics.find("[FN#") != -1:
            return "Lyrics not found"
        #se c'è 50 o più volte il carattere " nella stringa ritorna Lyrics not found
        if song.lyrics.count('"') >= 50:
            return "Lyrics not found"
        lyrics = song.lyrics.split('\n', 1)[-1]
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

def get_genre_artist(artist_name, token):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)
    params = {
        "q": artist_name,
        "type": "artist",
        "limit": "1"
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()  # Raise an exception for HTTP errors
    json_result = response.json()["artists"]["items"]

    if not json_result:
        print("No artist found")
        return None
    
    if not json_result[0]["genres"]:
        return "not applicable"

    if not json_result[0]["genres"][0]:
        return "not applicable"
    
    return json_result[0]["genres"][0]


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

@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/favorites")
def favorites():
    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")
    
    delete_double_songs_from_favorite(session["token"])
    songs_data = []
    global max_offset_for_favorites
    for i in range(0, 1000, 50):
        songs = get_favorite_songs(session["token"], i)
        if not songs:
            break
        for song in songs:
            image_url = "https://icpapagiovanni.edu.it/wp-content/uploads/2017/11/musica-1.jpg"
            if song["track"]["album"]["images"]:
                image_url = song["track"]["album"]["images"][0]["url"]
            song_data = {
                "name": song["track"]["name"],
                "artist": song["track"]["artists"][0]["name"],
                "image": image_url
            }
            songs_data.append(song_data)
        max_offset_for_favorites = i
        print("Max offset:", max_offset_for_favorites)
    
    return render_template("favorites.html", songs=songs_data)

@app.route("/playlists")
def playlists():
    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")
    
    headers = {
        "Authorization": "Bearer " + session["token"]
    }
    url = "https://api.spotify.com/v1/me/playlists"
    result = requests.get(url, headers=headers)
    json_result = jsonify(json.loads(result.content))

    playlists = []
    for playlist in json_result.json["items"]:
        image_url = "https://icpapagiovanni.edu.it/wp-content/uploads/2017/11/musica-1.jpg"  # Inizializza l'URL dell'immagine di default
        if playlist["images"]:  # Verifica se la lista delle immagini non è vuota
            image_url = playlist["images"][0]["url"]  # Assegna l'URL dell'immagine se disponibile
        playlist_data = {
            "name": playlist["name"],
            "id": playlist["id"],
            "image": image_url,
            "name": playlist["name"]
        }
        playlists.append(playlist_data)

    #return jsonify(json_result)
    return render_template("playlists.html", playlists=playlists)

@app.route("/artist/<artist_id>")
def artist(artist_id):
    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")
    
    headers = {
        "Authorization": "Bearer " + session["token"]
    }
    url = "https://api.spotify.com/v1/artists/" + artist_id
    result = requests.get(url, headers=headers)
    json_result = jsonify(json.loads(result.content))

    genres = ""
    for genre in json_result.json["genres"]:
        genres += genre + ", "
    genres = genres[:-2]

    artist_data = {
        "name": json_result.json["name"],
        "image": json_result.json["images"][0]["url"],
        "followers": json_result.json["followers"]["total"],
        "popularity": json_result.json["popularity"],
        "genres": genres,
        "id": artist_id
    }

    album_json = get_artist_albums(session["token"], artist_id)
    song_json = get_songs_by_artist(session["token"], artist_id)

    albums = []
    if album_json:
        for album in album_json:
            image_url = "https://icpapagiovanni.edu.it/wp-content/uploads/2017/11/musica-1.jpg"
            if album["images"]:
                image_url = album["images"][0]["url"]
            album_data = {
                "name": album["name"],
                "image": image_url,
                "id": album["id"],
                "artist": album["artists"][0]["name"]
            }
            albums.append(album_data)

    songs = []
    if song_json:
        for song in song_json:
            image_url = "https://icpapagiovanni.edu.it/wp-content/uploads/2017/11/musica-1.jpg"
            if song["album"]["images"]:
                image_url = song["album"]["images"][0]["url"]
            song_data = {
                "name": song["name"],
                "image": image_url,
                "artist": song["artists"][0]["name"]
            }
            songs.append(song_data)

    return render_template("artist.html", artist=artist_data, albums=albums, songs=songs)

@app.route("/albums/<album_id>")
def album(album_id):
    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")
    
    headers = {
        "Authorization": "Bearer " + session["token"]
    }
    url = "https://api.spotify.com/v1/albums/" + album_id
    result = requests.get(url, headers=headers)
    json_result = jsonify(json.loads(result.content))

    album_data = {
        "name": json_result.json["name"],
        "image": json_result.json["images"][0]["url"],
        "id": album_id
    }

    song_json = get_album_songs(session["token"], album_id)

    songs = []
    for song in song_json:
        song_data = {
            "name": song["name"],
            "artist": song["artists"][0]["name"],
            "image": json_result.json["images"][0]["url"]
        }
        songs.append(song_data)

    return render_template("album.html", album=album_data, songs=songs)

@app.route("/playlist/<playlist_id>/<playlist_name>")
def playlist(playlist_id, playlist_name):
    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")
    
    headers = {
        "Authorization": "Bearer " + session["token"]
    }
    url = "https://api.spotify.com/v1/playlists/" + playlist_id + "/tracks"
    result = requests.get(url, headers=headers)
    json_result = jsonify(json.loads(result.content))
    
    songs = []
    for song in json_result.json["items"]:
        song_data = {
            "name": song["track"]["name"],
            "artist": song["track"]["artists"][0]["name"],
            "image": song["track"]["album"]["images"][0]["url"]
        }
        songs.append(song_data)

    return render_template("songs.html", songs=songs, playlist_name=playlist_name, playlist_id=playlist_id)

@app.route("/download_playlist/<playlist_name>/<song_name>/<artist_name>")
def download_playlist(playlist_name, song_name, artist_name):
    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")
    
    song_name = urllib.parse.unquote(song_name)
    artist_name = urllib.parse.unquote(artist_name)
    link = find_song_on_youtube(song_name + " " + artist_name)
    
    if link:
        print("Link trovato:", link)
        save_path = "static/playlists/" + playlist_name + "/"
        saved_file = YoutubeAudioDownload(link, save_path, song_name, artist_name)
        
        if saved_file:
            return redirect(request.headers.get('Referer'))
        else:
            return "Errore nel scaricare il file audio."
    else:
        return "Canzone non trovata su YouTube."

@app.route("/download_all_playlist/<playlist_id>/<playlist_name>")
def download_all_playlist(playlist_id, playlist_name):
    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")

    songs = get_playlist_songs(session["token"], playlist_id)
    save_path = "static/playlists/" + playlist_name + "/"
    for song in songs:
        song_name = song["track"]["name"]
        artist_name = song["track"]["artists"][0]["name"]
        link = find_song_on_youtube(song_name + " " + artist_name)
        if link:
            print("Link trovato:", link)
            saved_file = YoutubeAudioDownload(link, save_path, song_name, artist_name)
            if not saved_file:
                return "Errore nel scaricare il file audio."
        else:
            return "Canzone non trovata su YouTube."
    
    return redirect(request.headers.get('Referer'))

@app.route("/download_album/<album_name>/<song_name>/<artist_name>")
def download_album(album_name, song_name, artist_name):
    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")
    
    song_name = urllib.parse.unquote(song_name)
    artist_name = urllib.parse.unquote(artist_name)
    link = find_song_on_youtube(song_name + " " + artist_name)
    
    if link:
        print("Link trovato:", link)
        save_path = "static/albums/" + album_name + "/"
        saved_file = YoutubeAudioDownload(link, save_path, song_name, artist_name)
        
        if saved_file:
            return redirect(request.headers.get('Referer'))
        else:
            return "Errore nel scaricare il file audio."
    else:
        return "Canzone non trovata su YouTube."

@app.route("/download_all_album/<album_id>/<album_name>")
def download_all_album(album_id, album_name):
    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")

    songs = get_album_songs(session["token"], album_id)
    save_path = "static/albums/" + album_name + "/"
    for song in songs:
        song_name = song["name"]
        artist_name = song["artists"][0]["name"]
        link = find_song_on_youtube(song_name + " " + artist_name)
        if link:
            print("Link trovato:", link)
            saved_file = YoutubeAudioDownload(link, save_path, song_name, artist_name)
            if not saved_file:
                return "Errore nel scaricare il file audio."
        else:
            return "Canzone non trovata su YouTube."
    
    return redirect(request.headers.get('Referer'))

@app.route("/download/<song_name>/<artist_name>")
def download(song_name, artist_name):
    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")
    
    song_name = urllib.parse.unquote(song_name)
    artist_name = urllib.parse.unquote(artist_name)
    link = find_song_on_youtube(song_name + " " + artist_name)
    
    if link:
        print("Link trovato:", link)
        save_path = "static/songs/"
        saved_file = YoutubeAudioDownload(link, save_path, song_name, artist_name)
        #se non l'ha scaricato, ritorna errore
        if saved_file:
            return redirect(request.headers.get('Referer'))
        else:
            return "Errore nel scaricare il file audio."
    else:
        return "Canzone non trovata su YouTube."

@app.route("/download_all_favorites")
def download_all_favorites():
    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")

    for i in range(0, 1000, 50):
        songs = get_favorite_songs(session["token"], i)
        if not songs:
            break
        save_path = "static/songs/"
        for song in songs:
            song_name = song["track"]["name"]
            artist_name = song["track"]["artists"][0]["name"]
            link = find_song_on_youtube(song_name + " " + artist_name)
            if link:
                print("Link trovato:", link)
                saved_file = YoutubeAudioDownload(link, save_path, song_name, artist_name)
                if not saved_file:
                    return "Errore nel scaricare il file audio."
            else:
                return "Canzone non trovata su YouTube."
    
    return redirect(request.headers.get('Referer'))

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

    return redirect("/playlists")

@app.route("/home")
def home():
    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")
    
    headers = {
        "Authorization": "Bearer " + session["token"]
    }
    url = "https://api.spotify.com/v1/browse/featured-playlists"
    result = requests.get(url, headers=headers)
    json_result = jsonify(json.loads(result.content))
    
    playlists = []
    for playlist in json_result.json["playlists"]["items"]:
        image_url = "https://icpapagiovanni.edu.it/wp-content/uploads/2017/11/musica-1.jpg"
        if playlist["images"]:
            image_url = playlist["images"][0]["url"]
        playlist_data = {
            "name": playlist["name"],
            "id": playlist["id"],
            "image": image_url,
            "name": playlist["name"]
        }
        playlists.append(playlist_data)

    #return jsonify(json_result)
    return render_template("home.html", playlists=playlists)

@app.route("/search")
def search_page():
    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")
    
    return render_template("search.html")

@app.route("/search/<search_query>")
def search(search_query):
    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")
    
    token = session["token"]
    artist_json = search_for_artist(token, search_query)
    album_json = search_for_album(token, search_query)
    song_json = search_for_song(token, search_query)
    playlist_json = search_for_playlist(token, search_query)

    artists = []
    if artist_json:
        for artist in artist_json:
            image_url = "https://icpapagiovanni.edu.it/wp-content/uploads/2017/11/musica-1.jpg"
            if artist["images"]:
                image_url = artist["images"][0]["url"]
            artist_data = {
                "name": artist["name"],
                "image": image_url,
                "id": artist["id"]
            }
            artists.append(artist_data)
    
    albums = []
    if album_json:
        for album in album_json:
            image_url = "https://icpapagiovanni.edu.it/wp-content/uploads/2017/11/musica-1.jpg"
            if album["images"]:
                image_url = album["images"][0]["url"]
            album_data = {
                "name": album["name"],
                "image": image_url,
                "id": album["id"],
                "artist": album["artists"][0]["name"]
            }
            albums.append(album_data)

    songs = []
    if song_json:
        for song in song_json:
            image_url = "https://icpapagiovanni.edu.it/wp-content/uploads/2017/11/musica-1.jpg"
            if song["album"]["images"]:
                image_url = song["album"]["images"][0]["url"]
            song_data = {
                "name": song["name"],
                "image": image_url,
                "artist": song["artists"][0]["name"]
            }
            songs.append(song_data)
    
    playlists = []
    if playlist_json:
        for playlist in playlist_json:
            image_url = "https://icpapagiovanni.edu.it/wp-content/uploads/2017/11/musica-1.jpg"
            if playlist["images"]:
                image_url = playlist["images"][0]["url"]
            playlist_data = {
                "name": playlist["name"],
                "id": playlist["id"],
                "image": image_url,
                "name": playlist["name"]
            }
            playlists.append(playlist_data)

    return render_template("search.html", artists=artists, albums=albums, songs=songs, playlists=playlists)

@app.route("/player/<playlist_id>/<song_name>/<artist_name>")
def player(playlist_id,song_name, artist_name):
    print("\n\n\n")
    song_name = html.unescape(song_name)
    artist_name = html.unescape(artist_name)

    print(song_name, artist_name)

    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")
    
    token = session["token"]
    link = find_song_on_youtube(song_name + " " + artist_name)
    #prendi tutto quello che c'è dopo https://www.youtube.com/watch?v=
    link = link[link.index("=")+1:]
    lyrics = get_lyrics(song_name, artist_name)
    #prendi le canzone della playlist, cerca la posizione della canzone e prendi la canzone precedente e successiva
    songs = get_playlist_songs(token, playlist_id)
    prev_song_name = ""
    prev_artist_name = ""
    next_song_name = ""
    next_artist_name = ""
    img = "https://icpapagiovanni.edu.it/wp-content/uploads/2017/11/musica-1.jpg"
    for i in range(len(songs)):
        if songs[i]["track"]["name"] == song_name and songs[i]["track"]["artists"][0]["name"] == artist_name:
            print("trovato")
            img = songs[i]["track"]["album"]["images"][0]["url"]
            if i > 0:
                prev_song_name = songs[i-1]["track"]["name"]
                prev_artist_name = songs[i-1]["track"]["artists"][0]["name"]
            if i < len(songs)-1:
                next_song_name = songs[i+1]["track"]["name"]
                next_artist_name = songs[i+1]["track"]["artists"][0]["name"]
            if i == 0:
                prev_song_name = songs[len(songs)-1]["track"]["name"]
                prev_artist_name = songs[len(songs)-1]["track"]["artists"][0]["name"]
            if i == (len(songs)-1):
                next_song_name = songs[0]["track"]["name"]
                next_artist_name = songs[0]["track"]["artists"][0]["name"]
            break
    print(prev_song_name, prev_artist_name, next_song_name, next_artist_name)

    song = {
        "name": song_name,
        "artist": artist_name,
        "image": img,
        "link": link,
        "lyrics": lyrics,
        "prev_name": prev_song_name,
        "prev_artist": prev_artist_name,
        "next_name": next_song_name,
        "next_artist": next_artist_name,
        "playlist_id": playlist_id
    }

    song_log = {
        "topic": "song_played",
        "name": song_name,
        "artist": artist_name,
        "lyrics": lyrics,
        "genre": get_genre_artist(artist_name, token),
        "id": search_for_song(token, song_name + artist_name)[0]["id"]
    }
    test_logger.info(json.dumps(song_log))
    return render_template("player.html", song=song)

@app.route("/player_album/<album_id>/<song_name>/<artist_name>")
def player_album(album_id,song_name, artist_name):
    print("\n\n\n")
    song_name = html.unescape(song_name)
    artist_name = html.unescape(artist_name)

    print(song_name, artist_name)

    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")
    
    token = session["token"]
    link = find_song_on_youtube(song_name + " " + artist_name)
    song_json = search_for_song(token, song_name + artist_name)[0]
    #prendi tutto quello che c'è dopo https://www.youtube.com/watch?v=
    link = link[link.index("=")+1:]
    lyrics = get_lyrics(song_name, artist_name)
    
    songs = get_album_songs(token, album_id)
    prev_song_name = ""
    prev_artist_name = ""
    next_song_name = ""
    next_artist_name = ""
    for i in range(len(songs)):
        if songs[i]["name"] == song_name and songs[i]["artists"][0]["name"] == artist_name:
            print("trovato")
            if i > 0:
                prev_song_name = songs[i-1]["name"]
                prev_artist_name = songs[i-1]["artists"][0]["name"]
            if i < len(songs)-1:
                next_song_name = songs[i+1]["name"]
                next_artist_name = songs[i+1]["artists"][0]["name"]
            if i == 0:
                prev_song_name = songs[len(songs)-1]["name"]
                prev_artist_name = songs[len(songs)-1]["artists"][0]["name"]
            if i == (len(songs)-1):
                next_song_name = songs[0]["name"]
                next_artist_name = songs[0]["artists"][0]["name"]
            break
    print(prev_song_name, prev_artist_name, next_song_name, next_artist_name)

    song = {
        "name": song_name,
        "artist": artist_name,
        "image": song_json["album"]["images"][0]["url"],
        "link": link,
        "lyrics": lyrics,
        "prev_name": prev_song_name,
        "prev_artist": prev_artist_name,
        "next_name": next_song_name,
        "next_artist": next_artist_name,
        "album_id": album_id
    }
    song_log = {
        "topic": "song_played",
        "name": song_name,
        "artist": artist_name,
        "lyrics": lyrics,
        "genre": get_genre_artist(artist_name, token),
        "id": search_for_song(token, song_name + artist_name)[0]["id"]
    }
    test_logger.info(json.dumps(song_log))
    return render_template("player_album.html", song=song)

@app.route("/player")
def empty_player():
    return render_template("empty_player.html")

@app.route("/player/<song_name>/<artist_name>")
def player_song(song_name, artist_name):
    print("\n\n\n")
    song_name = html.unescape(song_name)
    artist_name = html.unescape(artist_name)

    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")
    
    token = session["token"]
    song_json = search_for_song(token, song_name + artist_name)[0]
    link = find_song_on_youtube(song_name + " " + artist_name)
    #prendi tutto quello che c'è dopo https://www.youtube.com/watch?v=
    link = link[link.index("=")+1:]
    lyrics = get_lyrics(song_name, artist_name)
    song = {
        "name": song_name,
        "artist": artist_name,
        "image": song_json["album"]["images"][0]["url"],
        "link": link,
        "lyrics": lyrics
    }
    song_log = {
        "topic": "song_played",
        "name": song_name,
        "artist": artist_name,
        "lyrics": lyrics,
        "genre": get_genre_artist(artist_name, token),
        "id": search_for_song(token, song_name + artist_name)[0]["id"]
    }
    test_logger.info(json.dumps(song_log))
    return render_template("player_single_song.html", song=song)

@app.route("/player_artist/<artist_id>/<song_name>/<artist_name>")
def player_artist(artist_id,song_name, artist_name):
    print("\n\n\n")
    print("\n")
    song_name = html.unescape(song_name)
    artist_name = html.unescape(artist_name)

    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")
    
    token = session["token"]
    link = find_song_on_youtube(song_name + " " + artist_name)
    #prendi tutto quello che c'è dopo https://www.youtube.com/watch?v=
    link = link[link.index("=")+1:]
    lyrics = get_lyrics(song_name, artist_name)

    songs = get_songs_by_artist(token, artist_id)
    prev_song_name = ""
    prev_artist_name = ""
    next_song_name = ""
    next_artist_name = ""
    img = "https://icpapagiovanni.edu.it/wp-content/uploads/2017/11/musica-1.jpg"
    for i in range(len(songs)):
        if songs[i]["name"] == song_name and songs[i]["artists"][0]["name"] == artist_name:
            print("trovato")
            img = songs[i]["album"]["images"][0]["url"]
            if i > 0:
                prev_song_name = songs[i-1]["name"]
                prev_artist_name = songs[i-1]["artists"][0]["name"]
            if i < len(songs)-1:
                next_song_name = songs[i+1]["name"]
                next_artist_name = songs[i+1]["artists"][0]["name"]
            if i == 0:
                prev_song_name = songs[len(songs)-1]["name"]
                prev_artist_name = songs[len(songs)-1]["artists"][0]["name"]
            if i == (len(songs)-1):
                next_song_name = songs[0]["name"]
                next_artist_name = songs[0]["artists"][0]["name"]
            break
    print(prev_song_name, prev_artist_name, next_song_name, next_artist_name)

    song = {
        "name": song_name,
        "artist": artist_name,
        "image": img,
        "link": link,
        "lyrics": lyrics,
        "prev_name": prev_song_name,
        "prev_artist": prev_artist_name,
        "next_name": next_song_name,
        "next_artist": next_artist_name,
        "artist_id": artist_id
    }
    song_log = {
        "topic": "song_played",
        "name": song_name,
        "artist": artist_name,
        "lyrics": lyrics,
        "genre": get_genre_artist(artist_name, token),
        "id": search_for_song(token, song_name + artist_name)[0]["id"]
    }
    test_logger.info(json.dumps(song_log))
    return render_template("player_artist.html", song=song)

@app.route("/play_song/<song_name>/<artist_name>")
def play(song_name, artist_name):
    # Costruisci il percorso completo alla canzone
    song_path = os.path.join('songs', song_name + ' - ' + artist_name + '.mp3')
    # Restituisci il template HTML passando il percorso della canzone
    return render_template('play_songs.html', song_path=song_path)

@app.route("/player_favorite/<song_name>/<artist_name>")
def player_favorite(song_name, artist_name):
    print("\n\n\n")
    song_name = html.unescape(song_name)
    artist_name = html.unescape(artist_name)

    if "token" not in session:
        return redirect("/")
    
    if datetime.now().timestamp() > session["expires_at"]:
        return redirect("/refresh")
    
    token = session["token"]
    global max_offset_for_favorites
    link = find_song_on_youtube(song_name + " " + artist_name)
    link = link[link.index("=")+1:]
    lyrics = get_lyrics(song_name, artist_name)
    
    prev_song_name = ""
    prev_artist_name = ""
    next_song_name = ""
    next_artist_name = ""
    img = "https://icpapagiovanni.edu.it/wp-content/uploads/2017/11/musica-1.jpg"

    found = False
    offset = 0
    limit = 50

    while not found:
        songs = get_favorite_songs(token, offset)
        if not songs:
            break
        
        for i in range(len(songs)):
            if songs[i]["track"]["name"] == song_name and songs[i]["track"]["artists"][0]["name"] == artist_name:
                found = True
                img = songs[i]["track"]["album"]["images"][0]["url"]
                
                # Get previous song
                if i == 0:
                    if offset == 0:
                        prev_offset = max_offset_for_favorites 
                        print("prev offset se 0:", prev_offset)   #ok
                    else:
                        prev_offset = offset - limit
                        print("prev offset se no 0:", prev_offset)
                    prev_songs = get_favorite_songs(token, prev_offset)
                    if prev_songs:
                        prev_song = prev_songs[-1] 
                        prev_song_name = prev_song["track"]["name"]
                        prev_artist_name = prev_song["track"]["artists"][0]["name"]
                else:
                    prev_song_name = songs[i-1]["track"]["name"]
                    prev_artist_name = songs[i-1]["track"]["artists"][0]["name"]

                # Get next song
                if i == len(songs)-1:
                    if offset == max_offset_for_favorites:
                        next_offset = 0
                        print("next offset se max:", next_offset)
                    else:
                        next_offset = offset + limit
                        print("next offset se no max:", next_offset)
                    next_songs = get_favorite_songs(token, next_offset)
                    if next_songs:
                        next_song = next_songs[0]
                        next_song_name = next_song["track"]["name"]
                        next_artist_name = next_song["track"]["artists"][0]["name"]
                else:
                    next_song_name = songs[i+1]["track"]["name"]
                    next_artist_name = songs[i+1]["track"]["artists"][0]["name"]
                break
        
        offset += limit
    
    song = {
        "name": song_name,
        "artist": artist_name,
        "image": img,
        "link": link,
        "lyrics": lyrics,
        "prev_name": prev_song_name,
        "prev_artist": prev_artist_name,
        "next_name": next_song_name,
        "next_artist": next_artist_name
    }
    song_log = {
        "topic": "song_played",
        "name": song_name,
        "artist": artist_name,
        "lyrics": lyrics,
        "genre": get_genre_artist(artist_name, token),
        "id": search_for_song(token, song_name + artist_name)[0]["id"]
    }
    test_logger.info(json.dumps(song_log))
    return render_template("player_favorite.html", song=song)   

@app.route("/local")
def local():
    return render_template("local.html")

@app.route("/no_internet")
def no_internet():
    #restituisci a no_internet.html tutti i percorsi di tutti gli album, playlist e canzoni che sono nella cartella static
    albums = []
    for album in os.listdir("static/albums"):
        album_data = {
            "name": album,
            "path": "albums/" + album
        }
        albums.append(album_data)

    playlists = []
    for playlist in os.listdir("static/playlists"):
        playlist_data = {
            "name": playlist,
            "path": "playlists/" + playlist
        }
        playlists.append(playlist_data)
    
    songs = []
    for song in os.listdir("static/songs"):
        #il nome della canzone e l'artista sono separati da " - "
        #togli il ".mp3" dal nome della canzone
        name = song[:-4]
        name = name.split(" - ")
        song_data = {
            "name": name[0],
            "artist": name[1],
            "path": "songs/" + song
        }
        songs.append(song_data)

    #restituisci tutti gli artisti, confrontando ogni file all'interno delle cartelle albums, playlists e songs
    artists = []
    for album in os.listdir("static/albums"):
        for song in os.listdir("static/albums/" + album):
            name = song[:-4]
            name = name.split(" - ")
            if name[1] not in artists:
                artists.append(name[1])

    for playlist in os.listdir("static/playlists"): 
        for song in os.listdir("static/playlists/" + playlist):
            name = song[:-4]
            name = name.split(" - ")
            if name[1] not in artists:
                artists.append(name[1])

    for song in os.listdir("static/songs"):
        name = song[:-4]
        name = name.split(" - ")
        if name[1] not in artists:
            artists.append(name[1])
    
    return render_template("no_internet.html", albums=albums, playlists=playlists, songs=songs, artists=artists)

@app.route("/no_internet_album/<album_name>")
def no_internet_album(album_name):
    #restituisci a no_internet_album.html tutti i percorsi di tutte le canzoni che sono nella cartella static/albums/album_name
    songs = []
    for song in os.listdir("static/albums/" + album_name):
        #il nome della canzone e l'artista sono separati da " - "
        #togli il ".mp3" dal nome della canzone
        name = song[:-4]
        name = name.split(" - ")
        song_data = {
            "name": name[0],
            "artist": name[1],
            "path": "albums/" + album_name + "/" + song
        }
        songs.append(song_data)
    
    return render_template("no_internet_album.html", songs=songs, album_name=album_name)

@app.route("/no_internet_playlist/<playlist_name>")
def no_internet_playlist(playlist_name):
    #restituisci a no_internet_playlist.html tutti i percorsi di tutte le canzoni che sono nella cartella static/playlists/playlist_name
    songs = []
    for song in os.listdir("static/playlists/" + playlist_name):
        #il nome della canzone e l'artista sono separati da " - "
        #togli il ".mp3" dal nome della canzone
        name = song[:-4]
        name = name.split(" - ")
        song_data = {
            "name": name[0],
            "artist": name[1],
            "path": "playlists/" + playlist_name + "/" + song
        }
        songs.append(song_data)
    
    return render_template("no_internet_playlist.html", songs=songs, playlist_name=playlist_name)

@app.route("/no_internet_artist/<artist_name>")
def no_internet_artist(artist_name):
    #restituisci a no_internet_artist.html tutti i percorsi di tutte le canzoni che sono dell'artista nelle cartelle albums, playlists e songs
    songs = []
    for album in os.listdir("static/albums"):
        for song in os.listdir("static/albums/" + album):
            name = song[:-4]
            name = name.split(" - ")
            if name[1] == artist_name:
                song_data = {
                    "name": name[0],
                    "artist": name[1],
                    "path": "albums/" + album + "/" + song
                }
                songs.append(song_data)

    for playlist in os.listdir("static/playlists"):
        for song in os.listdir("static/playlists/" + playlist):
            name = song[:-4]
            name = name.split(" - ")
            if name[1] == artist_name:
                song_data = {
                    "name": name[0],
                    "artist": name[1],
                    "path": "playlists/" + playlist + "/" + song
                }
                songs.append(song_data)

    for song in os.listdir("static/songs"):
        name = song[:-4]
        name = name.split(" - ")
        if name[1] == artist_name:
            song_data = {
                "name": name[0],
                "artist": name[1],
                "path": "songs/" + song
            }
            songs.append(song_data)
    
    return render_template("no_internet_artist.html", songs=songs, artist_name=artist_name)

@app.route("/player_local")
def player_local_empty():
    return render_template("player_local_empty.html")

@app.route("/player_local/songs/<song_name>/<artist_name>")
def player_local(song_name, artist_name):
    song_name = html.unescape(song_name)
    artist_name = html.unescape(artist_name)
    song_path = "songs/" + song_name + " - " + artist_name + ".mp3"
    next_song_name = ""
    next_artist_name = ""
    prev_song_name = ""
    prev_artist_name = ""
    songs = os.listdir("static/songs")
    for i in range(len(songs)):
        if songs[i] == song_name + " - " + artist_name + ".mp3":
            if i > 0:
                prev_song_name = songs[i-1][:songs[i-1].index(" - ")]
                prev_artist_name = songs[i-1][songs[i-1].index(" - ")+3:-4]
            if i < len(songs)-1:
                next_song_name = songs[i+1][:songs[i+1].index(" - ")]
                next_artist_name = songs[i+1][songs[i+1].index(" - ")+3:-4]
            if i == 0:
                prev_song_name = songs[len(songs)-1][:songs[len(songs)-1].index(" - ")]
                prev_artist_name = songs[len(songs)-1][songs[len(songs)-1].index(" - ")+3:-4]
            if i == (len(songs)-1):
                next_song_name = songs[0][:songs[0].index(" - ")]
                next_artist_name = songs[0][songs[0].index(" - ")+3:-4]
            break
    print(prev_song_name, prev_artist_name, next_song_name, next_artist_name)

    return render_template("player_local.html", song_name=song_name, artist_name=artist_name, song_path=song_path, prev_song_name=prev_song_name, prev_artist_name=prev_artist_name, next_song_name=next_song_name, next_artist_name=next_artist_name)

@app.route("/player_local/playlists/<playlist_name>/<song_name>/<artist_name>")
def player_local_playlist(playlist_name, song_name, artist_name):
    song_name = html.unescape(song_name)
    artist_name = html.unescape(artist_name)
    song_path = "playlists/" + playlist_name + "/" + song_name + " - " + artist_name + ".mp3"
    next_song_name = ""
    next_artist_name = ""
    prev_song_name = ""
    prev_artist_name = ""
    songs = os.listdir("static/playlists/" + playlist_name)
    for i in range(len(songs)):
        if songs[i] == song_name + " - " + artist_name + ".mp3":
            if i > 0:
                prev_song_name = songs[i-1][:songs[i-1].index(" - ")]
                prev_artist_name = songs[i-1][songs[i-1].index(" - ")+3:-4]
            if i < len(songs)-1:
                next_song_name = songs[i+1][:songs[i+1].index(" - ")]
                next_artist_name = songs[i+1][songs[i+1].index(" - ")+3:-4]
            if i == 0:
                prev_song_name = songs[len(songs)-1][:songs[len(songs)-1].index(" - ")]
                prev_artist_name = songs[len(songs)-1][songs[len(songs)-1].index(" - ")+3:-4]
            if i == (len(songs)-1):
                next_song_name = songs[0][:songs[0].index(" - ")]
                next_artist_name = songs[0][songs[0].index(" - ")+3:-4]
            break
    print(prev_song_name, prev_artist_name, next_song_name, next_artist_name)

    return render_template("player_local_playlist.html", playlist_name=playlist_name, song_name=song_name, artist_name=artist_name, song_path=song_path, prev_song_name=prev_song_name, prev_artist_name=prev_artist_name, next_song_name=next_song_name, next_artist_name=next_artist_name)

@app.route("/player_local/albums/<album_name>/<song_name>/<artist_name>")
def player_local_album(album_name, song_name, artist_name):
    song_name = html.unescape(song_name)
    artist_name = html.unescape(artist_name)
    song_path = "albums/" + album_name + "/" + song_name + " - " + artist_name + ".mp3"
    next_song_name = ""
    next_artist_name = ""
    prev_song_name = ""
    prev_artist_name = ""
    songs = os.listdir("static/albums/" + album_name)
    for i in range(len(songs)):
        if songs[i] == song_name + " - " + artist_name + ".mp3":
            if i > 0:
                prev_song_name = songs[i-1][:songs[i-1].index(" - ")]
                prev_artist_name = songs[i-1][songs[i-1].index(" - ")+3:-4]
            if i < len(songs)-1:
                next_song_name = songs[i+1][:songs[i+1].index(" - ")]
                next_artist_name = songs[i+1][songs[i+1].index(" - ")+3:-4]
            if i == 0:
                prev_song_name = songs[len(songs)-1][:songs[len(songs)-1].index(" - ")]
                prev_artist_name = songs[len(songs)-1][songs[len(songs)-1].index(" - ")+3:-4]
            if i == (len(songs)-1):
                next_song_name = songs[0][:songs[0].index(" - ")]
                next_artist_name = songs[0][songs[0].index(" - ")+3:-4]
            break
    print(prev_song_name, prev_artist_name, next_song_name, next_artist_name)

    return render_template("player_local_album.html", album_name=album_name, song_name=song_name, artist_name=artist_name, song_path=song_path, prev_song_name=prev_song_name, prev_artist_name=prev_artist_name, next_song_name=next_song_name, next_artist_name=next_artist_name)

@app.route("/player_local/artists/<artist_name>/<song_name>")
def player_local_artist(artist_name, song_name):
    #prendi tutte le canzoni dell'artista da songs, albums e playlists e restituisci il percorso della canzone
    songs = []
    for song in os.listdir("static/songs"):
        name = song[:-4]
        name = name.split(" - ")
        if name[1] == artist_name:
            song_data = {
                "name": name[0],
                "artist": name[1],
                "path": "songs/" + song
            }
            songs.append(song_data)

    for album in os.listdir("static/albums"):
        for song in os.listdir("static/albums/" + album):
            name = song[:-4]
            name = name.split(" - ")
            if name[1] == artist_name:
                song_data = {
                    "name": name[0],
                    "artist": name[1],
                    "path": "albums/" + album + "/" + song
                }
                songs.append(song_data)

    for playlist in os.listdir("static/playlists"):
        for song in os.listdir("static/playlists/" + playlist):
            name = song[:-4]
            name = name.split(" - ")
            if name[1] == artist_name:
                song_data = {
                    "name": name[0],
                    "artist": name[1],
                    "path": "playlists/" + playlist + "/" + song
                }
                songs.append(song_data)

    song_name = html.unescape(song_name)
    artist_name = html.unescape(artist_name)
    song_path = ""
    next_song_name = ""
    next_artist_name = ""
    prev_song_name = ""
    prev_artist_name = ""
    for i in range(len(songs)):
        if songs[i]["name"] == song_name:
            song_path = songs[i]["path"]
            if i > 0:
                prev_song_name = songs[i-1]["name"]
                prev_artist_name = songs[i-1]["artist"]
            if i < len(songs)-1:
                next_song_name = songs[i+1]["name"]
                next_artist_name = songs[i+1]["artist"]
            if i == 0:
                prev_song_name = songs[len(songs)-1]["name"]
                prev_artist_name = songs[len(songs)-1]["artist"]
            if i == (len(songs)-1):
                next_song_name = songs[0]["name"]
                next_artist_name = songs[0]["artist"]
            break
    print(prev_song_name, prev_artist_name, next_song_name, next_artist_name)

    return render_template("player_local_artist.html", artist_name=artist_name, song_name=song_name, song_path=song_path, prev_song_name=prev_song_name, prev_artist_name=prev_artist_name, next_song_name=next_song_name, next_artist_name=next_artist_name)
    
@app.route("/delete_playlist/<playlist_name>")
def delete_playlist(playlist_name):
    print("Cancello la playlist", playlist_name)
    #elimina la cartella della playlist
    shutil.rmtree("static/playlists/" + playlist_name)
    return redirect(request.headers.get('Referer'))

@app.route("/delete_album/<album_name>")
def delete_album(album_name):
    print("Cancello l'album", album_name)
    #elimina la cartella dell'album
    shutil.rmtree("static/albums/" + album_name)
    return redirect(request.headers.get('Referer'))

@app.route("/delete_song/<song_name>/<artist_name>")
def delete_song(song_name, artist_name):
    print("Cancello la canzone", song_name, artist_name)
    #elimina il file della canzone
    os.remove("static/songs/" + song_name + " - " + artist_name + ".mp3")
    return redirect(request.headers.get('Referer'))

@app.route("/delete_from_playlist/<playlist_name>/<song_name>/<artist_name>")
def delete_from_playlist(playlist_name, song_name, artist_name):
    print("Cancello la canzone", song_name, artist_name, "dalla playlist", playlist_name)
    #elimina il file della canzone
    os.remove("static/playlists/" + playlist_name + "/" + song_name + " - " + artist_name + ".mp3")
    if not os.listdir("static/playlists/" + playlist_name):
        #se la cartella è vuota, cancellala
        os.rmdir("static/playlists/" + playlist_name)
        return redirect("/no_internet")
    else:
        return redirect(request.headers.get('Referer'))

@app.route("/delete_from_album/<album_name>/<song_name>/<artist_name>")
def delete_from_album(album_name, song_name, artist_name):
    print("Cancello la canzone", song_name, artist_name, "dall'album", album_name)
    #elimina il file della canzone
    os.remove("static/albums/" + album_name + "/" + song_name + " - " + artist_name + ".mp3")
    if not os.listdir("static/albums/" + album_name):
        #se la cartella è vuota, cancellala
        os.rmdir("static/albums/" + album_name)
        return redirect("/no_internet")
    else:
        return redirect(request.headers.get('Referer'))

@app.route("/delete_from_artist/<artist_name>/<song_name>")
def delete_from_artist(artist_name, song_name):
    #cancella la canzone da songs, albums e playlists
    print("Cancello la canzone", song_name, "dall'artista", artist_name)
    #elimina il file della canzone se è presente
    if os.path.exists("static/songs/" + song_name + " - " + artist_name + ".mp3"):
        os.remove("static/songs/" + song_name + " - " + artist_name + ".mp3")
    #elimina la canzone da albums
    for album in os.listdir("static/albums"):
        if os.path.exists("static/albums/" + album + "/" + song_name + " - " + artist_name + ".mp3"):
            os.remove("static/albums/" + album + "/" + song_name + " - " + artist_name + ".mp3")
            if not os.listdir("static/albums/" + album):
                #se la cartella è vuota, cancellala
                os.rmdir("static/albums/" + album)
    #elimina la canzone da playlists
    for playlist in os.listdir("static/playlists"):
        if os.path.exists("static/playlists/" + playlist + "/" + song_name + " - " + artist_name + ".mp3"):
            os.remove("static/playlists/" + playlist + "/" + song_name + " - " + artist_name + ".mp3")
            if not os.listdir("static/playlists/" + playlist):
                #se la cartella è vuota, cancellala
                os.rmdir("static/playlists/" + playlist)

    return redirect("/no_internet_artist/" + artist_name)
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
