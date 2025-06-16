import sys
import os
import re
import time
import logging
import winreg

from PyQt6.QtWidgets import QApplication, QWidget, QMenu, QSystemTrayIcon
from PyQt6.QtCore import Qt, QPoint, QThread, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtGui import QFont, QColor, QWheelEvent, QMouseEvent, QPainter, QBrush, QPen, QFontMetrics, QIcon

import spotipy
import lyricsgenius
import syncedlyrics

# --- Configuração de Caminhos e Constantes ---
APP_NAME = "LetrasPIP"
CACHE_DIR = os.path.join(os.getenv('APPDATA'), APP_NAME)
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
CACHE_FILE = os.path.join(CACHE_DIR, ".spotipyoauthcache")
RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

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
            SPOTIPY_CLIENT_ID = '6859bf6df1fa4b0e998a90d794aaa884'
            SPOTIPY_CLIENT_SECRET = 'adf235e1983a4c9f9a358192773314f2'
            SPOTIPY_REDIRECT_URI = 'http://127.0.0.1:8888/callback'
            auth_manager = spotipy.SpotifyOAuth(
                scope="user-read-playback-state",
                client_id=SPOTIPY_CLIENT_ID,
                client_secret=SPOTIPY_CLIENT_SECRET,
                redirect_uri=SPOTIPY_REDIRECT_URI,
                cache_path=CACHE_FILE
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
        except Exception as e:
            self.lyrics_data_ready.emit({'text': f"Erro de autenticação: {e}", 'parsed': [], 'progress': 0})

    def setup_genius(self):
        try:
            GENIUS_ACCESS_TOKEN = 'qlvL0KeFAapheVmiMPMMrRP0JV3slDCmHpt30H_trG3o_QZjUNaiLHPXL4uC9uUQ'
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
                self.lyrics_data_ready.emit({'text': self.current_lyrics_text, 'parsed': self.parsed_lyrics, 'progress': progress_ms + 500})
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
        self.setup_tray_icon()
        self.init_ui()
        self.spotify_thread = SpotifyThread(self)
        self.spotify_thread.lyrics_data_ready.connect(self.update_lyrics_data)
        self.spotify_thread.start()

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(resource_path('icon.ico')))
        self.tray_icon.setToolTip("LetrasPIP Spotify")
        tray_menu = QMenu()
        show_hide_action = tray_menu.addAction("Mostrar/Esconder Letras")
        show_hide_action.triggered.connect(self.toggle_visibility)
        tray_menu.addSeparator()
        self.startup_action = tray_menu.addAction("Iniciar com o Windows")
        self.startup_action.setCheckable(True)
        if getattr(sys, 'frozen', False):
            self.startup_action.setChecked(self.is_in_startup())
            self.startup_action.triggered.connect(self.toggle_startup)
        else:
            self.startup_action.setEnabled(False)
            self.startup_action.setToolTip("Disponível apenas na versão instalada")
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("Fechar")
        quit_action.triggered.connect(QApplication.instance().quit)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visibility()

    def toggle_visibility(self):
        self.setVisible(not self.isVisible())

    def is_in_startup(self):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False

    def set_startup(self, enable):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_ALL_ACCESS) as key:
                if enable:
                    executable_path = f'"{sys.executable}"'
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, executable_path)
                else:
                    winreg.DeleteValue(key, APP_NAME)
        except Exception:
            pass

    def toggle_startup(self):
        self.set_startup(self.startup_action.isChecked())

    def closeEvent(self, event):
        self.hide()
        event.ignore()

    def init_ui(self):
        self.setWindowIcon(QIcon(resource_path('icon.ico')))
        self.setWindowTitle('Letras PIP Spotify')
        self.setGeometry(100, 100, 400, 250)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

    def enable_snap_back(self):
        self.user_has_scrolled = False
        self.manual_scroll_offset = 0
        self.update()

    @pyqtSlot(dict)
    def update_lyrics_data(self, data):
        new_parsed_lyrics = data.get('parsed', [])
        progress_ms = data.get('progress', 0)
        self.text_content = data.get('text', '')

        if self.parsed_lyrics != new_parsed_lyrics:
            self.parsed_lyrics = new_parsed_lyrics
            self.manual_scroll_offset = 0
            # Auto-ajusta a largura da janela
            font = QFont('Arial', 22); font.setBold(True)
            fm = QFontMetrics(font)
            max_width = max(fm.horizontalAdvance(line) for _, line in self.parsed_lyrics) if self.parsed_lyrics else 0
            self.resize(max(max_width + 40, 400), self.height())

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
            painter.setFont(QFont('Arial', 12))
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
                color = QColor(220, 220, 220)
                color.setAlphaF(opacity)
                painter.setPen(QPen(color))
                y_pos = view_center_y + (distance_from_center * line_height)
                fm = QFontMetrics(font)
                x_pos = (self.width() - fm.horizontalAdvance(line_text)) // 2
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
