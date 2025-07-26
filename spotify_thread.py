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
from spotipy.oauth2 import SpotifyOAuth
import srt

def parse_srt(srt_text):
    parsed_lyrics = []
    for sub in srt.parse(srt_text):
        start_ms = int(sub.start.total_seconds() * 1000)
        end_ms = int(sub.end.total_seconds() * 1000)
        clean_text = sub.content.strip().replace('\n', ' ')
        if clean_text and not clean_text.isdigit():
            parsed_lyrics.append((start_ms, end_ms, clean_text))
    return parsed_lyrics

def parse_lrc(lrc_text):
    if not lrc_text:
        return []
    lrc_line_regex = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)')
    times = []
    texts = []
    
    # Processa linha por linha do LRC
    for line in lrc_text.splitlines():
        match = lrc_line_regex.match(line)
        if match:
            minutes, seconds, hundredths, text = match.groups()
            if len(hundredths) == 2:
                hundredths = f"{hundredths}0"
            time_ms = int(minutes) * 60000 + int(seconds) * 1000 + int(hundredths)
            clean_text = text.strip()
            if clean_text:  # Só adiciona se tiver texto
                times.append(time_ms)
                texts.append(clean_text)
    
    # Gera blocos (start, end, text)
    parsed_blocks = []
    MIN_VERSO_DURATION = 4000  # mínimo de 4 segundos por verso
    parsed_blocks = []
    last_text_block = None
    last_start = None
    for i in range(len(times)):
        start = times[i]
        text = texts[i].strip()
        if not text:
            continue  # pula blocos vazios
        # Busca próximo índice com texto não vazio
        next_idx = i + 1
        while next_idx < len(times) and not texts[next_idx].strip():
            next_idx += 1
        if next_idx < len(times):
            end = times[next_idx]
            # Garante duração mínima
            if end - start < MIN_VERSO_DURATION:
                end = start + MIN_VERSO_DURATION
        else:
            end = start + 600000
        parsed_blocks.append((start, end, text))
    return parsed_blocks

def parse_synced_lyrics(synced_result, log_fn=print):
    """Processa letras sincronizadas em diversos formatos.

    Parameters
    ----------
    synced_result : Any
        Resultado retornado pelo SyncedLyrics (string LRC ou lista de dicts).
    log_fn : callable
        Função de logging para depuração (default: print).
    """
    try:
        # Formato string LRC
        if isinstance(synced_result, str) and '[' in synced_result:
            log_fn("[THREAD] Detectado formato LRC (string)")
            return parse_lrc(synced_result)

        # Formato lista de dicts (API antiga)
        if isinstance(synced_result, list) and all(isinstance(line, dict) for line in synced_result):
            log_fn("[THREAD] Detectado formato lista de dicts")
            parsed = []
            for i, line in enumerate(synced_result):
                start = int(line['time'])
                text = line.get('text', '').strip()
                if text:
                    end = int(synced_result[i+1]['time']) if i+1 < len(synced_result) else start + 10000
                    parsed.append((start, end, text))
            return parsed

        log_fn(f"[THREAD] Formato não reconhecido: {type(synced_result)}")
        return []

    except Exception as e:
        log_fn(f"[THREAD] Erro ao processar letra sincronizada: {str(e)}")
        return []

class SpotifyThread(QThread):
    lyrics_data_ready = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.spotify_client = None
        self.genius_client = lyricsgenius.Genius(config.GENIUS_ACCESS_TOKEN)
        self.synced_lyrics_client = syncedlyrics
        self.last_track_id = None
        self.cached_offset = 0
        self.is_running = True
        self.log_window = parent.log_window if parent else None
        self.setup_spotify_client()

    def setup_spotify_client(self):
        try:
            # Garantir que o diretório de cache existe
            if not os.path.exists(config.CACHE_DIR):
                os.makedirs(config.CACHE_DIR)

            # Configurar o gerenciador de autenticação
            auth_manager = SpotifyOAuth(
                client_id=config.SPOTIPY_CLIENT_ID,
                client_secret=config.SPOTIPY_CLIENT_SECRET,
                redirect_uri=config.SPOTIPY_REDIRECT_URI,
                scope="user-read-playback-state",
                cache_path=config.CACHE_FILE,
                open_browser=False
            )

            # Tentar criar o cliente Spotify
            self.spotify_client = spotipy.Spotify(auth_manager=auth_manager)
            
            # Testar a conexão
            self.spotify_client.current_user()
            self.log("Conexão com Spotify estabelecida com sucesso!")
            
        except Exception as e:
            self.log(f"Erro ao configurar cliente Spotify: {str(e)}")
            if self.spotify_client:
                self.spotify_client = None
            raise

    def log(self, message):
        """Wrapper para logging que verifica se log_window existe"""
        if self.log_window:
            self.log_window.add_log(message)
        print(message)

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

    def setup_genius(self):
        try:
            if config.GENIUS_ACCESS_TOKEN and config.GENIUS_ACCESS_TOKEN != 'SEU_GENIUS_ACCESS_TOKEN_AQUI':
                self.genius = lyricsgenius.Genius(config.GENIUS_ACCESS_TOKEN, verbose=False, remove_section_headers=True, timeout=15)
            else:
                self.genius = None
        except Exception as e:
            self.genius = None

    def run(self):
        self.log("[THREAD] Loop rodando...")
        while True:
            try:
                if not self.spotify_client:
                    self.spotify_client = spotipy.Spotify(auth_manager=SpotifyOAuth(
                        client_id=config.SPOTIPY_CLIENT_ID,
                        client_secret=config.SPOTIPY_CLIENT_SECRET,
                        redirect_uri=config.SPOTIPY_REDIRECT_URI,
                        scope="user-read-playback-state",
                        open_browser=False
                    ))
                
                current_playback = self.spotify_client.current_playback()
                
                if not current_playback or not current_playback.get('is_playing', False):
                    self.lyrics_data_ready.emit({'text': "Nenhuma música tocando...", 'parsed': []})
                    time.sleep(1)
                    continue

                track = current_playback['item']
                if not track:
                    self.lyrics_data_ready.emit({'text': "Nenhuma música tocando...", 'parsed': []})
                    time.sleep(1)
                    continue

                current_track_id = track['id']
                current_progress = current_playback.get('progress_ms', 0)
                
                # Se mudou de música, busca letra nova
                if current_track_id != self.last_track_id:
                    self.log(f"[THREAD] Buscando letra para: {track['name']} - {', '.join(artist['name'] for artist in track['artists'])}")
                    
                    # Busca no Genius
                    self.log(f"[THREAD] Buscando letras em Genius para: {track['name']} - {', '.join(artist['name'] for artist in track['artists'])}")
                    genius_result = self.genius_client.search_song(track['name'], ', '.join(artist['name'] for artist in track['artists']))
                    self.log(f"[THREAD] Resultado Genius (original): {genius_result is not None}")
                    
                    if genius_result:
                        self.log("[THREAD] Letra encontrada no Genius!")
                        self.log(f"[THREAD] Texto da letra (sem tags): {genius_result.lyrics[:100]}...")
                        
                        # Busca letra sincronizada
                        try:
                            self.log(f"[THREAD] Buscando letras em SyncedLyrics para: {track['name']} - {', '.join(artist['name'] for artist in track['artists'])}")
                            synced_result = self.synced_lyrics_client.search(f"{track['name']} {', '.join(artist['name'] for artist in track['artists'])}")
                            self.log(f"[THREAD] Resultado SyncedLyrics (original): {synced_result is not None}")
                        except Exception as sync_exc:
                            import traceback, io
                            tb_str = ''.join(traceback.format_exception(sync_exc))
                            self.log(f"[THREAD] EXCEÇÃO em SyncedLyrics.search:\n{tb_str}")
                            synced_result = None
                        
                        try:
                            # Processa a letra sincronizada
                            parsed_lyrics = parse_synced_lyrics(synced_result, self.log)
                            if parsed_lyrics:
                                self.log(f"[THREAD] Letras sincronizadas parseadas: {len(parsed_lyrics)} blocos")
                                # Log detalhado do primeiro e último bloco para debug
                                if len(parsed_lyrics) > 0:
                                    first_block = parsed_lyrics[0]
                                    last_block = parsed_lyrics[-1]
                                    self.log(f"[THREAD] Primeiro bloco: {first_block[0]}ms -> {first_block[1]}ms")
                                    self.log(f"[THREAD] Último bloco: {last_block[0]}ms -> {last_block[1]}ms")
                                
                                self.lyrics_data_ready.emit({
                                    'text': genius_result.lyrics,
                                    'parsed': parsed_lyrics,
                                    'progress': current_progress,
                                    'cached_offset': self.cached_offset
                                })
                            else:
                                self.log("[THREAD] Nenhum bloco sincronizado válido encontrado")
                                self.lyrics_data_ready.emit({
                                    'text': genius_result.lyrics,
                                    'parsed': [],
                                    'progress': current_progress,
                                    'cached_offset': self.cached_offset
                                })
                        except Exception as e:
                            self.log(f"[THREAD] Erro ao processar SyncedLyrics: {e}")
                            self.lyrics_data_ready.emit({
                                'text': genius_result.lyrics,
                                'parsed': [],
                                'progress': current_progress,
                                'cached_offset': self.cached_offset
                            })
                    else:
                        self.lyrics_data_ready.emit({
                            'text': "Letra não encontrada...",
                            'parsed': [],
                            'progress': current_progress,
                            'cached_offset': self.cached_offset
                        })
                    
                    self.last_track_id = current_track_id
                else:
                    # Apenas atualiza o progresso
                    self.lyrics_data_ready.emit({
                        'progress': current_progress,
                        'cached_offset': self.cached_offset
                    })
                
                time.sleep(0.1)  # Reduz intervalo para melhor sincronização
                
            except Exception as e:
                self.log(f"[THREAD] Erro: {str(e)}")
                self.spotify_client = None  # Força reconexão
                time.sleep(5)
