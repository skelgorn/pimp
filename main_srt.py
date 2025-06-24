import re
import os
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import QTimer
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import config


def parse_srt(srt_text):
    if not srt_text:
        return []
    parsed_lyrics = []
    # Extrai blocos padrão SRT
    srt_block_regex = re.compile(r"(\d+)\s*\n([\d:,]+)\s+-->\s+([\d:,]+)\s*\n([\s\S]*?)(?=\n\d+\n|\Z)", re.MULTILINE)
    for match in srt_block_regex.finditer(srt_text):
        idx, start, end, text = match.groups()
        h, m, s_ms = start.split(":")
        s, ms = s_ms.split(",")
        time_ms = int(h)*3600000 + int(m)*60000 + int(s)*1000 + int(ms)
        clean_text = text.strip().replace('\n', ' ')
        # Ignora blocos sem texto ou só com número/whitespace
        if clean_text and not clean_text.isdigit():
            parsed_lyrics.append((time_ms, clean_text))
    # Extrai linhas inline (número tempo --> tempo texto)
    srt_inline_regex = re.compile(r"(\d+)\s+([\d:,]+)\s+-->\s+([\d:,]+)\s+(.*)")
    for match in srt_inline_regex.finditer(srt_text):
        idx, start, end, text = match.groups()
        h, m, s_ms = start.split(":")
        s, ms = s_ms.split(",")
        time_ms = int(h)*3600000 + int(m)*60000 + int(s)*1000 + int(ms)
        clean_text = text.strip()
        if clean_text and not clean_text.isdigit():
            parsed_lyrics.append((time_ms, clean_text))
    return sorted(parsed_lyrics, key=lambda x: x[0])


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
            return
        # Avança para o verso correto
        idx = 0
        for i, (t, _) in enumerate(self.parsed_lyrics):
            if progress_ms >= t:
                idx = i
            else:
                break
        self.current_line_index = idx
        self.label.setText(self.parsed_lyrics[self.current_line_index][1])


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