import re
import os
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import QTimer
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import config
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


class SRTLyricsWindow(QWidget):
    def __init__(self, parsed_lyrics, sp, track_id):
        super().__init__()
        self.parsed_lyrics = parsed_lyrics
        self.current_line_index = 0
        self.label = QLabel("", self)
        self.label.setStyleSheet("font-size: 22px; color: white; background: #222; padding: 20px; border-radius: 10px;")
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.setWindowTitle("SRT Teste - LetrasPIP")
        self.setGeometry(200, 200, 600, 120)
        self.setStyleSheet("background: #222;")
        self.timer = QTimer(self)
        self.timer.setInterval(300)  # 300 ms
        self.timer.timeout.connect(self.update_lyrics)
        self.sp = sp
        self.track_id = track_id

    def start(self):
        self.timer.start()

    def get_spotify_progress(self):
        try:
            playback = self.sp.current_playback()
            if playback and playback.get('item') and playback['item']['id'] == self.track_id:
                return playback['progress_ms']
        except Exception as e:
            pass
        return None

    def update_lyrics(self):
        progress_ms = self.get_spotify_progress()
        if progress_ms is None:
            self.label.setText("Aguardando Spotify...")
            print("[DEBUG] Aguardando Spotify...")
            return

        # Lista só com blocos que têm texto
        text_blocks = [(start, end, text) for start, end, text in self.parsed_lyrics if text.strip()]
        current_text = ""
        for i, (start, end, text) in enumerate(text_blocks):
            # Se estamos antes do início do primeiro verso, não mostra nada
            if progress_ms < start:
                break
            # Se estamos entre este verso e o próximo, ou depois do último, mostra este verso
            if i == len(text_blocks) - 1 or progress_ms < text_blocks[i + 1][0]:
                current_text = text
        print(f"[DEBUG] Exibindo: '{current_text}'\n")
        self.label.setText(current_text)


def main():
    # Autentica no Spotify
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        scope="user-read-playback-state",
        client_id=config.SPOTIPY_CLIENT_ID,
        client_secret=config.SPOTIPY_CLIENT_SECRET,
        redirect_uri=config.SPOTIPY_REDIRECT_URI,
        cache_path=config.CACHE_FILE
    ))
    playback = sp.current_playback()
    if not playback or not playback.get('item'):
        print("Nenhuma música tocando no Spotify.")
        sys.exit(1)
    track = playback['item']
    track_name = track['name']
    track_id = track['id']
    # Busca arquivo SRT pelo nome da música
    srt_filename = f"{track_name}.srt.txt"
    if not os.path.exists(srt_filename):
        print(f"Arquivo SRT '{srt_filename}' não encontrado.")
        sys.exit(1)
    with open(srt_filename, 'r', encoding='utf-8') as f:
        srt_text = f.read()
    parsed_lyrics = parse_srt(srt_text)
    app = QApplication(sys.argv)
    window = SRTLyricsWindow(parsed_lyrics, sp, track_id)
    window.show()
    window.start()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

# No ponto onde carrega a letra, tente SRT primeiro, depois LRC
# Exemplo de uso:
#   if os.path.exists(srt_path):
#       with open(srt_path, 'r', encoding='utf-8') as f:
#           srt_text = f.read()
#       parsed_lyrics = parse_srt(srt_text)
#   elif os.path.exists(lrc_path):
#       with open(lrc_path, 'r', encoding='utf-8') as f:
#           lrc_text = f.read()
#       parsed_lyrics = parse_lrc(lrc_text)
#   else:
#       parsed_lyrics = [] 