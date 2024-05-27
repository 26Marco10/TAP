import os
import base64
import requests
import json
import lyricsgenius
import logging
import logstash
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
genius_token = os.getenv("GENIUS_API_TOKEN")

# Set up Logstash
host = 'localhost'
port = 5959
test_logger = logging.getLogger('logstash')
test_logger.setLevel(logging.INFO)
test_logger.addHandler(logstash.TCPLogstashHandler(host, port, version=1))

# Set up ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=10)

def get_token():
    auth_string = f"{client_id}:{client_secret}"
    auth_bytes = auth_string.encode('utf-8')
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "client_credentials"
    }

    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()  # Raise an exception for HTTP errors
    json_result = response.json()
    return json_result["access_token"]

def get_auth_header(token):
    return {
        "Authorization": f"Bearer {token}"
    }

def search_for_playlist(token, playlist_name):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)
    params = {
        "q": playlist_name,
        "type": "playlist",
        "limit": "1"
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()  # Raise an exception for HTTP errors
    json_result = response.json()["playlists"]["items"]

    if not json_result:
        print("No playlist found")
        return None

    return json_result[0]

def get_playlist_songs(token, playlist_id):
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = get_auth_header(token)
    params = {
        "limit": "100"
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()  # Raise an exception for HTTP errors
    return response.json()["items"]

def get_lyrics(song_name, artist_name):
    genius = lyricsgenius.Genius(genius_token)
    song_name = song_name.split('[')[0].split('(')[0].strip()
    song = genius.search_song(song_name, artist_name)

    if song:
        lyrics = song.lyrics.split('\n', 1)[-1]
        return lyrics
    else:
        return "Lyrics not found"

def produce_song_global_top(songs):
    print("Producing songs...")
    for song in songs:
        track = song["track"]
        lyrics = get_lyrics(track["name"], track["artists"][0]["name"])
        song_data = {
            "topic": "song_global_top",
            "name": track["name"],
            "artist": track["artists"][0]["name"],
            "lyrics": lyrics,
            "id": track["id"]
        }
        test_logger.info(json.dumps(song_data))

def main():
    token = get_token()
    top_global_playlist = search_for_playlist(token, "Top 50 Globale")

    if top_global_playlist:
        top_global_songs = get_playlist_songs(token, top_global_playlist["id"])
        executor.submit(produce_song_global_top, top_global_songs)

if __name__ == "__main__":
    main()