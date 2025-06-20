# spotify_thread.py

import re
import time
import os
import spotipy
import lyricsgenius
import syncedlyrics
import config
from PyQt5.QtCore import QThread, pyqtSignal
from func_timeout import func_timeout, FunctionTimedOut

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
            clean_text = text.strip()
            if clean_text:
                parsed_lyrics.append((time_ms, clean_text))
    return sorted(parsed_lyrics, key=lambda x: x[0])

class SpotifyThread(QThread):
    lyrics_data_ready = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = True
        self.sp = None
        self.genius = None
        self.current_track_id = None
        self.parsed_lyrics = []
        self.current_lyrics_text = "Conectando..."
        self.sync_offset = 0
        self.current_artist = None
        self.current_song_title = None

    def set_sync_offset(self, offset):
        self.sync_offset = offset

    def get_sync_offset(self):
        return self.sync_offset

    def force_genius_search(self):
        if not self.genius or not self.current_track_id:
            return

        song_title_original = self.current_song_title
        self.lyrics_data_ready.emit({'text': f"Buscando no Genius:\n{song_title_original}...", 'parsed': [], 'progress': 0})
        
        try:
            song = func_timeout(5, self.genius.search_song, args=[song_title_original, self.current_artist])
            if song and song.lyrics:
                self.parsed_lyrics = []
                lyrics_body = re.sub(r'^(.*Lyrics)\n', '', song.lyrics, 1).strip()
                lyrics_body = re.sub(r'\d*Embed$', '', lyrics_body).strip()
                lyrics_text_only = re.sub(r'\[.*?\]|\(.*?\)', '', lyrics_body).strip()

                if len(lyrics_text_only) < 50:
                    self.lyrics_data_ready.emit({'text': f"Letra não encontrada no Genius para:\n{song_title_original}", 'parsed': [], 'progress': 0})
                else:
                    self.current_lyrics_text = lyrics_body
                    playback = self.sp.current_playback()
                    progress_ms = playback.get('progress_ms', 0) if playback else 0
                    self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': progress_ms + 500})
            else:
                self.lyrics_data_ready.emit({'text': f"Letra não encontrada no Genius para:\n{song_title_original}", 'parsed': [], 'progress': 0})
        except FunctionTimedOut:
            self.lyrics_data_ready.emit({'text': f"Busca no Genius demorou demais para:\n{song_title_original}", 'parsed': [], 'progress': 0})
        except Exception:
            self.lyrics_data_ready.emit({'text': f"Erro na busca do Genius.", 'parsed': [], 'progress': 0})

    def stop(self):
        self.is_running = False

    def setup_spotify(self):
        if self.sp:
            return
        
        try:
            auth_manager = spotipy.SpotifyOAuth(
                scope="user-read-playback-state",
                client_id=config.SPOTIPY_CLIENT_ID,
                client_secret=config.SPOTIPY_CLIENT_SECRET,
                redirect_uri=config.SPOTIPY_REDIRECT_URI,
                cache_path=config.CACHE_FILE
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            try:
                self.sp.current_user()
                self.lyrics_data_ready.emit({'text': "Conectado ao Spotify!", 'parsed': [], 'progress': 0})
            except:
                self.sp = None
                raise
        except Exception as e:
            self.lyrics_data_ready.emit({'text': f"Erro ao iniciar Spotify: {e}", 'parsed': [], 'progress': 0})
            self.sp = None

    def setup_genius(self):
        try:
            if config.GENIUS_ACCESS_TOKEN and config.GENIUS_ACCESS_TOKEN != 'SEU_GENIUS_ACCESS_TOKEN_AQUI':
                self.genius = lyricsgenius.Genius(config.GENIUS_ACCESS_TOKEN, verbose=False, remove_section_headers=True, timeout=15)
            else:
                self.genius = None
        except Exception as e:
            self.genius = None

    def run(self):
        self.lyrics_data_ready.emit({'text': "Conectando ao Spotify...", 'parsed': [], 'progress': 0})
        self._last_progress_ms = None
        
        BLACKLISTED_TITLES = [
            "[untitled]",
            "[instrumental]",
            "[intro]",
            "[outro]",
            "[interlude]",
            "[skit]",
            "[spoken]"
        ]
        
        INSTRUMENTAL_WORDS = [
            "instrumental",
            "untitled",
            "intro",
            "outro",
            "interlude",
            "skit",
            "spoken"
        ]

        def clean_title(title):
            title = re.sub(r'\[.*?\]', '', title)
            title = re.sub(r'\(.*?\)', '', title)
            title = title.replace(';', '').replace(',', '')
            title = re.sub(r'\s+', ' ', title).strip()
            return title.lower()

        try:
            self.setup_spotify()
            if not self.sp:
                raise Exception("Falha na conexão")
            self.sp.current_user()
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 401:
                self.lyrics_data_ready.emit({'text': "Sessão do Spotify expirada.\nPor favor, reinicie o aplicativo.", 'parsed': [], 'progress': 0, 'error': True})
                if os.path.exists(config.CACHE_FILE):
                    os.remove(config.CACHE_FILE)
            else:
                self.lyrics_data_ready.emit({'text': f"Erro de autenticação: {e.msg}", 'parsed': [], 'progress': 0, 'error': True})
            return
        except Exception as e:
            self.lyrics_data_ready.emit({'text': f"Falha na autenticação.\nPor favor, reinicie o app.", 'parsed': [], 'progress': 0, 'error': True})
            return

        self.lyrics_data_ready.emit({'text': "Nenhuma música tocando...", 'parsed': [], 'progress': 0})
        self.setup_genius()
        
        while self.is_running:
            try:
                playback = self.sp.current_playback()
                if not playback:
                    self.lyrics_data_ready.emit({'text': "Erro ao obter dados do Spotify", 'parsed': [], 'progress': 0})
                    time.sleep(1)
                    continue

                progress_ms = playback.get('progress_ms', 0)
                # Log detalhado do progresso
                if self._last_progress_ms is not None:
                    print(f"[SPOTIFY DEBUG] progress_ms anterior: {self._last_progress_ms}, atual: {progress_ms}, diferença: {progress_ms - self._last_progress_ms} | Música: {playback['item']['name']} - {playback['item']['artists'][0]['name']}")
                else:
                    print(f"[SPOTIFY DEBUG] progress_ms inicial: {progress_ms} | Música: {playback['item']['name']} - {playback['item']['artists'][0]['name']}")
                self._last_progress_ms = progress_ms

                if not playback['is_playing'] or not playback.get('item'):
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
                    self.current_artist = playback['item']['artists'][0]['name']
                    song_title_original = playback['item']['name']
                    self.current_song_title = song_title_original
                    artist = self.current_artist
                    print(f"[LYRICS FETCH DEBUG] Tocando agora: {song_title_original} - {artist}")
                    
                    if any(title.lower() in song_title_original.lower() for title in BLACKLISTED_TITLES):
                        self.parsed_lyrics = []
                        self.current_lyrics_text = f"Letra não encontrada para:\n{song_title_original}"
                        lyrics_found = False
                        self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': progress_ms + 500})
                        continue

                    if any(word.lower() in song_title_original.lower() for word in INSTRUMENTAL_WORDS):
                        self.parsed_lyrics = []
                        self.current_lyrics_text = f"Letra não encontrada para:\n{song_title_original}"
                        lyrics_found = False
                        self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': progress_ms + 500})
                        continue

                    cleaned_title = clean_title(song_title_original)
                    self.lyrics_data_ready.emit({'text': f"Buscando letra para:\n{song_title_original}...", 'parsed': [], 'progress': progress_ms})

                    lyrics_found = False
                    
                    try:
                        print(f"[LYRICS FETCH DEBUG] Buscando letra para: {song_title_original} - {artist}")
                        print(f"Buscando letras em SyncedLyrics para: {song_title_original} - {artist}")
                        lrc_lyrics = func_timeout(5, syncedlyrics.search, args=[f"{song_title_original} {artist}"])
                        print(f"Resultado SyncedLyrics (original): {bool(lrc_lyrics)}")
                        
                        if not lrc_lyrics:
                            print(f"Tentando novamente com título limpo: {cleaned_title}")
                            lrc_lyrics = func_timeout(5, syncedlyrics.search, args=[f"{cleaned_title} {artist}"])
                        
                        parsed_lrc = parse_lrc(lrc_lyrics) if lrc_lyrics else []
                        print(f"Letras parseadas: {len(parsed_lrc)}")
                        
                        if parsed_lrc:
                            self.parsed_lyrics = parsed_lrc
                            self.current_lyrics_text = "\n".join([line for _, line in self.parsed_lyrics])
                            lyrics_found = True
                            print(f"Letra encontrada via SyncedLyrics!")
                            self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': progress_ms + 500})
                            continue
                        else:
                            text_from_lrc = "".join([line for _, line in parsed_lrc])
                            text_only_from_lrc = re.sub(r'\[.*?\]|\(.*?\)', '', text_from_lrc).strip()
                            if len(text_only_from_lrc) > 30:
                                self.parsed_lyrics = []
                                self.current_lyrics_text = text_only_from_lrc
                                lyrics_found = True
                                print(f"Letra encontrada via SyncedLyrics!")
                                self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': progress_ms + 500})
                                continue
                    except FunctionTimedOut:
                        print(f"Timeout na busca SyncedLyrics para: {song_title_original}")
                    except Exception as e:
                        print(f"Erro na busca SyncedLyrics: {e}")
                        pass

                    if not lyrics_found and self.genius:
                        try:
                            print(f"Buscando letras em Genius para: {song_title_original} - {artist}")
                            song = func_timeout(5, self.genius.search_song, args=[song_title_original, artist])
                            print(f"Resultado Genius (original): {bool(song)}")
                            
                            if not song or not song.lyrics:
                                print(f"Tentando novamente com título limpo: {cleaned_title}")
                                song = func_timeout(5, self.genius.search_song, args=[cleaned_title, artist])
                                print(f"Resultado Genius (limpo): {bool(song)}")
                            
                            self.parsed_lyrics = []
                            if song and song.lyrics:
                                lyrics_lower = song.lyrics.lower()
                                print(f"Letra encontrada no Genius!")
                                
                                if "this song is an instrumental" in lyrics_lower or "lyrics for this song have yet to be released" in lyrics_lower:
                                    print("Letra é instrumental ou não lançada")
                                    self.current_lyrics_text = f"Letra não encontrada para:\n{song_title_original}"
                                else:
                                    lyrics_body = re.sub(r'^(.*Lyrics)\n', '', song.lyrics, 1).strip()
                                    lyrics_body = re.sub(r'\d*Embed$', '', lyrics_body).strip()
                                    lyrics_text_only = re.sub(r'\[.*?\]|\(.*?\)', '', lyrics_body).strip()
                                    print(f"Texto da letra (sem tags): {lyrics_text_only[:100]}...")
                                    if len(lyrics_text_only) < 50:
                                        print("Letra muito curta")
                                        self.current_lyrics_text = f"Letra não encontrada para:\n{song_title_original}"
                                    else:
                                        self.current_lyrics_text = lyrics_body
                                        lyrics_found = True
                                        print("Letra encontrada e validada!")
                                        self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': progress_ms + 500})
                                        continue
                            else:
                                print("Nenhuma letra encontrada no Genius")
                                self.current_lyrics_text = f"Letra não encontrada para:\n{song_title_original}"
                        except FunctionTimedOut:
                            print("Timeout na busca Genius")
                        except Exception as e:
                            print(f"Erro na busca Genius: {e}")

                    self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': progress_ms + 500})

                    if lyrics_found:
                        continue

                    time.sleep(1)
                    continue

            except spotipy.exceptions.SpotifyException as e:
                self.lyrics_data_ready.emit({'text': "Sessão do Spotify expirada.\nPor favor, reinicie o aplicativo.", 'parsed': [], 'progress': 0})
                break
            except Exception as e:
                self.lyrics_data_ready.emit({'text': "Erro ao buscar dados. Reconectando...", 'parsed': [], 'progress': 0})
                self.current_track_id = None
                time.sleep(10)
                break
