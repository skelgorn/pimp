# spotify_thread.py

import re
import time
import os
import spotipy
import lyricsgenius
import syncedlyrics
import config
from PyQt6.QtCore import QThread, pyqtSignal
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
        self.parent_window = parent

    def log(self, message):
        """Envia log para a janela principal se disponível"""
        if hasattr(self.parent_window, 'log_window'):
            self.parent_window.log_window.add_log(f"[THREAD] {message}")
        print(f"[THREAD] {message}")

    def get_cached_offset(self, artist, title):
        """Obtém o offset salvo para uma faixa específica"""
        if hasattr(self.parent_window, 'get_cached_offset'):
            return self.parent_window.get_cached_offset(artist, title)
        return 0

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
                    self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': progress_ms})
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
        
        last_track_id = None
        manual_progress_ms = 0
        last_real_progress_ms = 0
        last_playback_time = time.time()
        while self.is_running:
            print('[THREAD] Loop rodando...')
            try:
                playback = self.sp.current_playback()
                if not playback:
                    self.lyrics_data_ready.emit({'text': "Erro ao obter dados do Spotify", 'parsed': [], 'progress': 0})
                    time.sleep(1)
                    continue
                if not playback['is_playing'] or not playback.get('item'):
                    if self.current_track_id is not None:
                        self.lyrics_data_ready.emit({'text': "Nenhuma música tocando...", 'parsed': [], 'progress': 0})
                        self.current_track_id = None
                        self.parsed_lyrics = []
                    manual_progress_ms = 0
                    last_real_progress_ms = 0
                    last_track_id = None
                    time.sleep(1)
                    continue
                track_id = playback['item']['id']
                progress_ms = playback.get('progress_ms', 0)
                # Se mudou de faixa, reseta o progresso manual
                if track_id != last_track_id:
                    manual_progress_ms = progress_ms
                    last_real_progress_ms = progress_ms
                    last_track_id = track_id
                    last_playback_time = time.time()
                else:
                    # Se a API não atualiza, incrementa manualmente
                    if progress_ms == last_real_progress_ms:
                        manual_progress_ms += int((time.time() - last_playback_time) * 1000)
                    else:
                        manual_progress_ms = progress_ms
                        last_real_progress_ms = progress_ms
                    last_playback_time = time.time()

                if track_id != self.current_track_id:
                    self.current_track_id = track_id
                    self.current_artist = playback['item']['artists'][0]['name']
                    song_title_original = playback['item']['name']
                    self.current_song_title = song_title_original
                    artist = self.current_artist
                    
                    # Carrega offset salvo para esta faixa
                    cached_offset = self.get_cached_offset(artist, song_title_original)
                    if cached_offset != 0:
                        self.log(f"Offset carregado para '{artist} - {song_title_original}': {cached_offset}ms")
                        # Emite um sinal para atualizar o offset na janela principal
                        self.lyrics_data_ready.emit({'text': f"Carregando offset salvo...", 'parsed': [], 'progress': manual_progress_ms, 'cached_offset': cached_offset})
                    
                    if any(title.lower() in song_title_original.lower() for title in BLACKLISTED_TITLES):
                        self.parsed_lyrics = []
                        self.current_lyrics_text = f"Letra não encontrada para:\n{song_title_original}"
                        lyrics_found = False
                        self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': manual_progress_ms})
                        continue

                    if any(word.lower() in song_title_original.lower() for word in INSTRUMENTAL_WORDS):
                        self.parsed_lyrics = []
                        self.current_lyrics_text = f"Letra não encontrada para:\n{song_title_original}"
                        lyrics_found = False
                        self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': manual_progress_ms})
                        continue

                    cleaned_title = clean_title(song_title_original)
                    self.log(f"Buscando letra para: {song_title_original} - {artist}")
                    self.lyrics_data_ready.emit({'text': f"Buscando letra para:\n{song_title_original}...", 'parsed': [], 'progress': manual_progress_ms})

                    lyrics_found = False
                    
                    try:
                        self.log(f"Buscando letras em SyncedLyrics para: {song_title_original} - {artist}")
                        lrc_lyrics = func_timeout(5, syncedlyrics.search, args=[f"{song_title_original} {artist}"])
                        self.log(f"Resultado SyncedLyrics (original): {bool(lrc_lyrics)}")
                        
                        if not lrc_lyrics:
                            self.log(f"Tentando novamente com título limpo: {cleaned_title}")
                            lrc_lyrics = func_timeout(5, syncedlyrics.search, args=[f"{cleaned_title} {artist}"])
                        
                        parsed_lrc = parse_lrc(lrc_lyrics) if lrc_lyrics else []
                        self.log(f"Letras parseadas: {len(parsed_lrc)}")
                        # Nova regra: se só tem uma linha e é vocalize/curta, tratar como instrumental
                        if len(parsed_lrc) == 1:
                            only_line = parsed_lrc[0][1].strip()
                            vocalize_patterns = [r'^([dlh ]*-?)+$', r'^(la|de|doo|dum|na|oh|ah|ba|pa|da|la)+[ .,!-]*$', r'^\W*$']
                            is_vocalize = any(re.match(pat, only_line.lower()) for pat in vocalize_patterns)
                            if len(only_line) < 15 or is_vocalize:
                                self.log("Letra sincronizada considerada instrumental por ser muito curta ou vocalize.")
                                self.parsed_lyrics = []
                                self.current_lyrics_text = f"Letra não encontrada para:\n{song_title_original} (Instrumental)"
                                lyrics_found = False
                                self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': [], 'progress': manual_progress_ms})
                                continue
                        if parsed_lrc:
                            self.parsed_lyrics = parsed_lrc
                            self.current_lyrics_text = "\n".join([line for _, line in self.parsed_lyrics])
                            lyrics_found = True
                            self.log(f"Letra encontrada via SyncedLyrics!")
                            self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': manual_progress_ms})
                            continue
                    except FunctionTimedOut:
                        self.log(f"Timeout na busca SyncedLyrics para: {song_title_original}")
                    except Exception as e:
                        self.log(f"Erro na busca SyncedLyrics: {e}")
                        pass

                    if not lyrics_found and self.genius:
                        try:
                            self.log(f"Buscando letras em Genius para: {song_title_original} - {artist}")
                            song = func_timeout(5, self.genius.search_song, args=[song_title_original, artist])
                            self.log(f"Resultado Genius (original): {bool(song)}")
                            
                            if not song or not song.lyrics:
                                self.log(f"Tentando novamente com título limpo: {cleaned_title}")
                                song = func_timeout(5, self.genius.search_song, args=[cleaned_title, artist])
                                self.log(f"Resultado Genius (limpo): {bool(song)}")
                            
                            self.parsed_lyrics = []
                            if song and song.lyrics:
                                lyrics_lower = song.lyrics.lower()
                                self.log(f"Letra encontrada no Genius!")
                                
                                if "this song is an instrumental" in lyrics_lower or "lyrics for this song have yet to be released" in lyrics_lower:
                                    self.log("Letra é instrumental ou não lançada")
                                    self.current_lyrics_text = f"Letra não encontrada para:\n{song_title_original}"
                                else:
                                    # Limpeza robusta para remover cabeçalhos e descrições do Genius
                                    # 1. Remove o cabeçalho "xxx Lyrics"
                                    lyrics_body = re.sub(r'^.*?lyrics\n?', '', song.lyrics, 1, flags=re.IGNORECASE | re.DOTALL)
                                    # 2. Encontra a primeira marca de seção (ex: [Verse 1]) e remove tudo antes dela
                                    first_section_match = re.search(r'\[(.*?)\]', lyrics_body)
                                    if first_section_match:
                                        lyrics_body = lyrics_body[first_section_match.start():]
                                    
                                    # 3. Remove a contagem de "Embed" no final
                                    lyrics_body = re.sub(r'\d*Embed$', '', lyrics_body).strip()
                                    
                                    # Validação final para garantir que temos uma letra
                                    lyrics_text_only = re.sub(r'\[.*?\]|\(.*?\)', '', lyrics_body).strip()
                                    self.log(f"Texto da letra (sem tags): {lyrics_text_only[:100]}...")
                                    # Nova regra: letra muito curta ou só vocalize = instrumental
                                    vocalize_patterns = [r'^([dlh ]*-?)+$', r'^(la|de|doo|dum|na|oh|ah|ba|pa|da|la)+[ .,!-]*$', r'^\W*$']
                                    is_vocalize = any(re.match(pat, lyrics_text_only.lower()) for pat in vocalize_patterns)
                                    if len(lyrics_text_only) < 15 or is_vocalize:
                                        self.log("Letra considerada instrumental por ser muito curta ou vocalize.")
                                        self.current_lyrics_text = f"Letra não encontrada para:\n{song_title_original} (Instrumental)"
                                    elif len(lyrics_text_only) < 50:
                                        self.current_lyrics_text = lyrics_body
                                        lyrics_found = True
                                        self.log("Letra encontrada e validada!")
                                        self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': manual_progress_ms})
                                        continue
                            else:
                                self.log("Nenhuma letra encontrada no Genius")
                                self.current_lyrics_text = f"Letra não encontrada para:\n{song_title_original}"
                        except FunctionTimedOut:
                            self.log("Timeout na busca Genius")
                        except Exception as e:
                            self.log(f"Erro na busca Genius: {e}")

                    self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': manual_progress_ms})

                    if lyrics_found:
                        continue

                # --- NOVA LÓGICA DE SINCRONIZAÇÃO AUTOMÁTICA ---
                # Se já temos letras sincronizadas para a faixa atual, continue emitindo o progresso atualizado
                if self.parsed_lyrics:
                    self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': manual_progress_ms})
                    time.sleep(0.5)
                    continue
                # ------------------------------------------------

                # Se não há letras sincronizadas, apenas aguarde
                self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': manual_progress_ms})
                time.sleep(1)
                continue

            except spotipy.exceptions.SpotifyException as e:
                print(f'[THREAD] SpotifyException: {e}')
                self.lyrics_data_ready.emit({'text': "Sessão do Spotify expirada.\nPor favor, reinicie o aplicativo.", 'parsed': [], 'progress': 0})
                time.sleep(5)
                continue
            except Exception as e:
                print(f'[THREAD] Exception inesperada: {e}')
                self.lyrics_data_ready.emit({'text': "Erro ao buscar dados. Reconectando...", 'parsed': [], 'progress': 0})
                self.current_track_id = None
                time.sleep(5)
                continue
