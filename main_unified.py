import re
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import QTimer, Qt
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import config
import lyricsgenius
import syncedlyrics

# --- Parsers Unificados ---
def needs_interpolation(parsed_lyrics, max_block_ms=4000):
    return any((end - start) > max_block_ms for start, end, text in parsed_lyrics)

def interpolate_long_blocks(parsed_lyrics, max_block_ms=4000, interp_ms=1000):
    new_lyrics = []
    for start, end, text in parsed_lyrics:
        duration = end - start
        if duration > max_block_ms:
            t = start
            while t + interp_ms < end:
                new_lyrics.append((t, t + interp_ms, text))
                t += interp_ms
            new_lyrics.append((t, end, text))
        else:
            new_lyrics.append((start, end, text))
    return new_lyrics

def parse_synced_lyrics(synced_result):
    if isinstance(synced_result, str) and '[' in synced_result:
        lrc_line_regex = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\]\s*(.*)')
        times = []
        texts = []
        for line in synced_result.splitlines():
            match = lrc_line_regex.match(line)
            if match:
                minutes, seconds, hundredths, text = match.groups()
                if len(hundredths) == 2: hundredths = f"{hundredths}0"
                time_ms = int(minutes) * 60000 + int(seconds) * 1000 + int(hundredths)
                clean_text = text.strip()
                times.append(time_ms)
                texts.append(clean_text)
        parsed_blocks = []
        for i, (start, text) in enumerate(zip(times, texts)):
            if not text:
                continue
            end = times[i+1] if i+1 < len(times) else start + 10000
            parsed_blocks.append((start, end, text))
            # Inserir bloco de instrumental se intervalo for maior que 5s
            if i+1 < len(times) and times[i+1] - end > 5000:
                print(f'[DEBUG] Bloco de instrumental inserido: {end} -> {times[i+1]}')
                parsed_blocks.append((end, times[i+1], "[Instrumental]"))
        parsed = parsed_blocks
        if needs_interpolation(parsed):
            print('[DEBUG] Interpolando blocos longos para melhor efeito do offset.')
            parsed = interpolate_long_blocks(parsed)
        return parsed
    elif isinstance(synced_result, list) and all(isinstance(line, dict) for line in synced_result):
        parsed = []
        for i, line in enumerate(synced_result):
            start = int(line['time'])
            text = line.get('text', '').strip()
            if text:
                end = int(synced_result[i+1]['time']) if i+1 < len(synced_result) else start + 10000
                parsed.append((start, end, text))
                # Inserir bloco de instrumental se intervalo for maior que 5s
                if i+1 < len(synced_result) and int(synced_result[i+1]['time']) - end > 5000:
                    print(f'[DEBUG] Bloco de instrumental inserido: {end} -> {int(synced_result[i+1]["time"])}')
                    parsed.append((end, int(synced_result[i+1]['time']), "[Instrumental]"))
        parsed = parsed
        if needs_interpolation(parsed):
            print('[DEBUG] Interpolando blocos longos para melhor efeito do offset.')
            parsed = interpolate_long_blocks(parsed)
        return parsed
    return []

def clean_lyrics_text(lyrics):
    # Remove apenas cabeçalhos/metadados comuns do Genius
    lines = lyrics.splitlines()
    cleaned = []
    for line in lines:
        if any(word in line.lower() for word in ["contributor", "lyrics", "embed"]):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()

# --- Janela Unificada ---
class UnifiedLyricsWindow(QWidget):
    def __init__(self, sp):
        super().__init__()
        self.parsed_lyrics = [(0, 9999999, "Aguardando Spotify...")]
        self.current_line_index = 0
        self.label = QLabel("", self)
        self.label.setStyleSheet("font-size: 22px; color: white; background: #222; padding: 20px; border-radius: 10px;")
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.setWindowTitle("Unificado SRT/LRC - LetrasPIP")
        self.setGeometry(200, 200, 600, 120)
        self.setStyleSheet("background: #222;")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.timer = QTimer(self)
        self.timer.setInterval(300)  # 300 ms
        self.timer.timeout.connect(self.update_lyrics)
        self.sp = sp
        self.track_id = None
        self.offset = 0  # Offset em ms
        self.genius = lyricsgenius.Genius(config.GENIUS_ACCESS_TOKEN, timeout=15)
        print('[DEBUG] UnifiedLyricsWindow inicializada')

        # Tentar buscar playback algumas vezes antes de desistir
        found_playback = False
        for attempt in range(10):  # tenta por ~3 segundos
            progress_ms, track_id, track_name, artist_name, is_playing = self.get_spotify_progress()
            print(f'[DEBUG] Tentativa {attempt+1}: progress_ms={progress_ms}, track_id={track_id}, track_name={track_name}, artist_name={artist_name}')
            if track_id is not None:
                print(f'[DEBUG] Inicialização: buscando letra para música já tocando: {track_name} - {artist_name}')
                self.track_id = track_id
                self.parsed_lyrics = self.fetch_lyrics(track_name, artist_name)
                self.current_line_index = 0
                self.offset = 0
                found_playback = True
                break
            QApplication.processEvents()  # permite refresh da UI
            QTimer.singleShot(300, lambda: None)  # espera 300ms
        if not found_playback:
            print('[DEBUG] Não encontrou playback ativo após tentativas iniciais.')
        self.update_lyrics()

    def start(self):
        self.timer.start()
        print('[DEBUG] Timer iniciado')

    def get_spotify_progress(self):
        try:
            playback = self.sp.current_playback()
            if playback and playback.get('item'):
                is_playing = playback.get('is_playing', True)
                return playback['progress_ms'], playback['item']['id'], playback['item']['name'], ', '.join(artist['name'] for artist in playback['item']['artists']), is_playing
        except Exception as e:
            print(f'[DEBUG] Erro ao obter progresso do Spotify: {e}')
        return None, None, None, None, None

    def fetch_lyrics(self, track_name, artist_name):
        try:
            print(f'[DEBUG] Buscando letra para: {track_name} - {artist_name}')
            genius_result = self.genius.search_song(track_name, artist_name)
            print(f'[DEBUG] genius_result: {genius_result}')
            if genius_result and genius_result.lyrics:
                try:
                    synced_result = syncedlyrics.search(f"{track_name} {artist_name}")
                    parsed_lyrics = parse_synced_lyrics(synced_result)
                    print(f'[DEBUG] parsed_lyrics (synced): {parsed_lyrics[:2]} ...')
                except Exception as e:
                    print(f'[DEBUG] Erro ao buscar letra sincronizada: {e}')
                    parsed_lyrics = []
                if not parsed_lyrics:
                    print('[DEBUG] Não encontrou letra sincronizada, usando letra simples.')
                    lyrics_text = clean_lyrics_text(genius_result.lyrics)
                    parsed_lyrics = [(0, 9999999, lyrics_text)]
            else:
                print('[DEBUG] Letra não encontrada no Genius.')
                parsed_lyrics = [(0, 9999999, "Letra não encontrada...")]
        except Exception as e:
            print(f'[DEBUG] Erro ao buscar letra online: {e}')
            parsed_lyrics = [(0, 9999999, "Erro ao buscar letra online.")]
        print(f'[DEBUG] Resultado final parsed_lyrics: {parsed_lyrics[:2]} ...')
        return parsed_lyrics

    def update_lyrics(self):
        progress_ms, track_id, track_name, artist_name, is_playing = self.get_spotify_progress()
        if track_id is None:
            new_text = f"Aguardando Spotify...\nOffset: {self.offset/1000:.2f}s"
            if self.label.text() != new_text:
                self.label.setText(new_text)
            return
        if is_playing is False:
            new_text = f"Música pausada\nOffset: {self.offset/1000:.2f}s"
            if self.label.text() != new_text:
                self.label.setText(new_text)
            return
        if self.track_id != track_id:
            self.track_id = track_id
            self.parsed_lyrics = self.fetch_lyrics(track_name, artist_name)
            self.current_line_index = 0
            self.offset = 0
        if progress_ms is None:
            new_text = f"Aguardando Spotify...\nOffset: {self.offset/1000:.2f}s"
            if self.label.text() != new_text:
                self.label.setText(new_text)
            return
        progress_with_offset = progress_ms + self.offset
        current_text = ""
        sincronizada = True
        # Sempre mostrar o último verso anterior, mesmo durante buracos
        for i, (start, end, text) in enumerate(self.parsed_lyrics):
            if start <= progress_with_offset < end:
                current_text = text
                break
        else:
            # Se não caiu em nenhum bloco, mostra o último verso anterior
            for i in reversed(range(len(self.parsed_lyrics))):
                if self.parsed_lyrics[i][0] <= progress_with_offset:
                    current_text = self.parsed_lyrics[i][2]
                    break
        if len(self.parsed_lyrics) == 1 and self.parsed_lyrics[0][0] == 0 and self.parsed_lyrics[0][1] > 9000000:
            sincronizada = False
        if sincronizada:
            new_text = f"{current_text}\n\nOffset: {self.offset/1000:.2f}s"
        else:
            new_text = f"{current_text}\n\nLetra não sincronizada — ajuste de offset indisponível."
        if self.label.text() != new_text:
            self.label.setText(new_text)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Left:
            self.offset -= 500
            print(f'[DEBUG] Offset diminuído: {self.offset}ms')
        elif event.key() == Qt.Key.Key_Right:
            self.offset += 500
            print(f'[DEBUG] Offset aumentado: {self.offset}ms')
        elif event.key() == Qt.Key.Key_R:
            self.offset = 0
            print(f'[DEBUG] Offset resetado para 0ms')
        self.update_lyrics()

# --- Main Unificado ---
def main():
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        scope="user-read-playback-state",
        client_id=config.SPOTIPY_CLIENT_ID,
        client_secret=config.SPOTIPY_CLIENT_SECRET,
        redirect_uri=config.SPOTIPY_REDIRECT_URI,
        cache_path=config.CACHE_FILE
    ))
    app = QApplication(sys.argv)
    window = UnifiedLyricsWindow(sp)
    window.show()
    window.start()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 