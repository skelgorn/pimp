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
        return parsed_blocks
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
        return parsed
    return []

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
                    parsed_lyrics = [(0, 9999999, genius_result.lyrics)]
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
        print(f'[DEBUG] is_playing: {is_playing}')
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
            print(f'[DEBUG] Mudou de faixa: {self.track_id} -> {track_id}')
            # Mudou de faixa, buscar nova letra
            self.track_id = track_id
            self.parsed_lyrics = self.fetch_lyrics(track_name, artist_name)
            print(f'[DEBUG] Blocos de letra criados: {len(self.parsed_lyrics)}')
            for i, (start, end, text) in enumerate(self.parsed_lyrics[:5]):  # Mostra os primeiros 5 blocos
                print(f'[DEBUG] Bloco {i}: {start}ms -> {end}ms: "{text[:50]}..."')
            self.current_line_index = 0
            self.offset = 0  # Resetar offset ao trocar de faixa
        if progress_ms is None:
            new_text = f"Aguardando Spotify...\nOffset: {self.offset/1000:.2f}s"
            if self.label.text() != new_text:
                self.label.setText(new_text)
            return
        # Aplique o offset ANTES de comparar com os blocos
        progress_with_offset = progress_ms + self.offset
        print(f'[DEBUG] Progresso: {progress_ms}ms + offset {self.offset}ms = {progress_with_offset}ms')
        current_text = ""
        sincronizada = True
        last_verse = ""
        selected_block_index = -1
        tolerance_ms = 1200  # tolerância para segurar o verso após instrumental (1.2s)
        for i, (start, end, text) in enumerate(self.parsed_lyrics):
            # O offset já foi aplicado, então toda a lógica usa progress_with_offset
            if progress_with_offset < start:
                break
            if i == len(self.parsed_lyrics) - 1 or progress_with_offset < self.parsed_lyrics[i + 1][0]:
                selected_block_index = i
                # Se o bloco atual é '[Instrumental]', mantenha o último verso não instrumental
                if text == "[Instrumental]":
                    current_text = last_verse
                    print(f'[DEBUG] Bloco instrumental selecionado ({i}), mantendo último verso: "{last_verse[:50]}..."')
                else:
                    # Se o próximo bloco não é instrumental, só troca se estiver dentro da tolerância
                    if i+1 < len(self.parsed_lyrics) and self.parsed_lyrics[i+1][0] - progress_with_offset > tolerance_ms and self.parsed_lyrics[i+1][2] != "[Instrumental]":
                        # Segura o verso atual
                        current_text = text
                        print(f'[DEBUG] Segurando verso ({i}): "{text[:50]}..." até {self.parsed_lyrics[i+1][0]}ms')
                    else:
                        current_text = text
                        last_verse = text
                        print(f'[DEBUG] Bloco selecionado ({i}): "{text[:50]}..."')
                break
        if selected_block_index == -1:
            print(f'[DEBUG] Nenhum bloco selecionado para progresso {progress_with_offset}ms')
        # Detectar se a letra é sincronizada (tem timestamps diferentes de 0)
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