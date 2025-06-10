import sys
import os
import re
import time
import spotipy
import lyricsgenius
import syncedlyrics
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QPoint, QThread, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtGui import QFont, QColor, QWheelEvent, QMouseEvent, QPainter, QBrush, QPen, QFontMetrics

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
            # --- PREENCHA SUAS CHAVES DO SPOTIFY AQUI ---
            SPOTIPY_CLIENT_ID = '6859bf6df1fa4b0e998a90d794aaa884'
            SPOTIPY_CLIENT_SECRET = 'adf235e1983a4c9f9a358192773314f2'
            SPOTIPY_REDIRECT_URI = 'http://127.0.0.1:8888/callback'
            # -------------------------------------------

            auth_manager = spotipy.SpotifyOAuth(
                scope="user-read-playback-state",
                client_id=SPOTIPY_CLIENT_ID,
                client_secret=SPOTIPY_CLIENT_SECRET,
                redirect_uri=SPOTIPY_REDIRECT_URI,
                cache_path=".spotipyoauthcache"
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
        except Exception as e:
            self.lyrics_data_ready.emit({'text': f"Erro de autenticação: {e}", 'parsed': [], 'progress': 0})

    def setup_genius(self):
        try:
            # --- PREENCHA SUA CHAVE DO GENIUS AQUI ---
            GENIUS_ACCESS_TOKEN = 'qlvL0KeFAapheVmiMPMMrRP0JV3slDCmHpt30H_trG3o_QZjUNaiLHPXL4uC9uUQ'
            # -----------------------------------------

            if GENIUS_ACCESS_TOKEN and GENIUS_ACCESS_TOKEN != 'SEU_GENIUS_ACCESS_TOKEN_AQUI':
                self.genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN, verbose=False, remove_section_headers=True, timeout=15)
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
                self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': progress_ms})
                time.sleep(0.25)
            except Exception as e:
                self.lyrics_data_ready.emit({'text': "Erro ao buscar dados. Reconectando...", 'parsed': [], 'progress': 0})
                self.current_track_id = None
                time.sleep(10)

class LyricsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.parsed_lyrics, self.current_line_index, self.manual_scroll_offset = [], -1, 0
        self.text_content, self._drag_pos = "Iniciando...", None
        self.user_has_scrolled = False
        self.scroll_snap_back_timer = QTimer(self)
        self.scroll_snap_back_timer.setSingleShot(True)
        self.scroll_snap_back_timer.setInterval(3000)
        self.scroll_snap_back_timer.timeout.connect(self.enable_snap_back)
        self.init_ui()
        self.spotify_thread = SpotifyThread(self)
        self.spotify_thread.lyrics_data_ready.connect(self.update_lyrics_data)
        self.spotify_thread.start()

    def init_ui(self):
        self.setWindowTitle('Letras PIP Spotify')
        self.setGeometry(100, 100, 600, 250)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

    def enable_snap_back(self):
        self.user_has_scrolled = False
        self.manual_scroll_offset = 0
        self.update()

    @pyqtSlot(dict)
    def update_lyrics_data(self, data):
        new_parsed_lyrics, progress_ms, self.text_content = data.get('parsed', []), data.get('progress', 0), data.get('text', '')
        if not new_parsed_lyrics:
            if self.parsed_lyrics: self.parsed_lyrics, self.current_line_index, self.manual_scroll_offset = [], -1, 0
            self.update()
            return
        if self.parsed_lyrics != new_parsed_lyrics: self.parsed_lyrics, self.manual_scroll_offset = new_parsed_lyrics, 0
        new_current_line_index = -1
        for i, (time, text) in enumerate(self.parsed_lyrics):
            if progress_ms >= time: new_current_line_index = i
            else: break
        if self.current_line_index != new_current_line_index:
            self.current_line_index = new_current_line_index
            if not self.user_has_scrolled:
                self.manual_scroll_offset = 0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(0, 0, 0, 1)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 10, 10)
        painter.setPen(QPen(Qt.GlobalColor.white))
        if not self.parsed_lyrics:
            font = QFont('Arial', 12)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text_content)
        else:
            line_height = 35
            total_lines_to_display = 5
            view_center_y = self.height() // 2
            view_center_index = max(0, min(self.current_line_index + self.manual_scroll_offset, len(self.parsed_lyrics) - 1))
            start_index = max(0, view_center_index - (total_lines_to_display // 2))
            end_index = min(len(self.parsed_lyrics), start_index + total_lines_to_display)
            for i in range(start_index, end_index):
                _, line_text = self.parsed_lyrics[i]
                is_current_line = (i == self.current_line_index)
                font = QFont('Arial')
                font.setBold(is_current_line)
                font.setPixelSize(22 if is_current_line else 18)
                painter.setFont(font)
                distance_from_center = i - view_center_index
                opacity = max(0, 1.0 - (abs(distance_from_center) * 0.25))
                color = QColor(255, 255, 255)
                if not is_current_line: color = QColor(220, 220, 220)
                color.setAlphaF(opacity)
                painter.setPen(QPen(color))
                y_pos = view_center_y + (distance_from_center * line_height)
                fm = QFontMetrics(font)
                text_width = fm.horizontalAdvance(line_text)
                x_pos = (self.width() - text_width) // 2
                painter.drawText(QPoint(x_pos, y_pos), line_text)

    def wheelEvent(self, event: QWheelEvent):
        if not self.parsed_lyrics: return
        self.user_has_scrolled = True
        self.scroll_snap_back_timer.start()
        delta = -1 if event.angleDelta().y() > 0 else 1
        self.manual_scroll_offset += delta
        max_offset = len(self.parsed_lyrics) - 1 - self.current_line_index
        min_offset = -self.current_line_index
        self.manual_scroll_offset = max(min_offset, min(self.manual_scroll_offset, max_offset))
        self.update()
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton: self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft(); event.accept()
    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos: self.move(event.globalPosition().toPoint() - self._drag_pos); event.accept()
    def mouseReleaseEvent(self, event: QMouseEvent): self._drag_pos = None; event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LyricsWindow()
    window.show()
    sys.exit(app.exec())
    main()

