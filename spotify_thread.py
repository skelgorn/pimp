# spotify_thread.py

import re
import time
import spotipy
import lyricsgenius
import syncedlyrics
import config
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication

def parse_lrc(lrc_text):
    if not lrc_text:
        return []
    parsed_lyrics = []
    lrc_line_regex = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\]\s*(.*)')
    for line in lrc_text.splitlines():
        match = lrc_line_regex.match(line)
        if match:
            minutes, seconds, hundredths, text = match.groups()
            if len(hundredths) == 2: hundredths = f"{hundredths}0"
            time_ms = int(minutes) * 60000 + int(seconds) * 1000 + int(hundredths)
            parsed_lyrics.append((time_ms, text.strip()))
    return sorted(parsed_lyrics, key=lambda x: x[0])

class SpotifyThread(QThread):
    lyrics_data_ready = pyqtSignal(dict)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sp = None
        self.genius = None
        self.current_track_id = None
        self.parsed_lyrics = []
        self.current_lyrics_text = "Iniciando..."

    def setup_spotify(self):
        try:
            auth_manager = spotipy.SpotifyOAuth(
                scope="user-read-playback-state",
                client_id=config.SPOTIPY_CLIENT_ID,
                client_secret=config.SPOTIPY_CLIENT_SECRET,
                redirect_uri=config.SPOTIPY_REDIRECT_URI,
                cache_path=config.CACHE_FILE
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
        except Exception as e:
            self.lyrics_data_ready.emit({'text': f"Erro de autenticação: {e}", 'parsed': [], 'progress': 0})

    def setup_genius(self):
        try:
            if config.GENIUS_ACCESS_TOKEN and config.GENIUS_ACCESS_TOKEN != 'SEU_GENIUS_ACCESS_TOKEN_AQUI':
                self.genius = lyricsgenius.Genius(config.GENIUS_ACCESS_TOKEN, verbose=False, remove_section_headers=True, timeout=15)
            else:
                self.genius = None
        except Exception as e:
            self.genius = None

    def run(self):
        self.setup_spotify()
        if not self.sp: return
        self.setup_genius()
        while True:
            try:
                playback = self.sp.current_playback()
                if not playback or not playback['is_playing']:
                    if self.current_track_id is not None:
                        self.lyrics_data_ready.emit({'text': "Nenhuma música tocando...", 'parsed': [], 'progress': 0})
                        self.current_track_id = None
                        self.parsed_lyrics = []
                    time.sleep(1)
                    continue
                track_id = playback['item']['id']
                progress_ms = playback.get('progress_ms', 0)
                if track_id != self.current_track_id:
                    self.current_track_id = track_id
                    artist, song_title = playback['item']['artists'][0]['name'], playback['item']['name']
                    search_term = f"{song_title} {artist}"
                    self.lyrics_data_ready.emit({'text': f"Buscando letra para:\n{song_title}...", 'parsed': [], 'progress': progress_ms})
                    QApplication.processEvents()
                    lrc_lyrics = syncedlyrics.search(search_term)
                    if lrc_lyrics and ']' in lrc_lyrics:
                        self.parsed_lyrics = parse_lrc(lrc_lyrics)
                        self.current_lyrics_text = "\n".join([line for _, line in self.parsed_lyrics]) if self.parsed_lyrics else ""
                    elif self.genius:
                        song = self.genius.search_song(song_title, artist)
                        self.parsed_lyrics = []
                        self.current_lyrics_text = song.lyrics.replace(f"{song_title} Lyrics", "").strip() if song and song.lyrics else f"Letra não encontrada para:\n{song_title}"
                    else:
                        self.parsed_lyrics = []
                        self.current_lyrics_text = f"{song_title}\n{artist}"
                self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': progress_ms + 500})
                time.sleep(0.25)
            except Exception as e:
                self.lyrics_data_ready.emit({'text': "Erro ao buscar dados. Reconectando...", 'parsed': [], 'progress': 0})
                self.current_track_id = None
                time.sleep(10)

