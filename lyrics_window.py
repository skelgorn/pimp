# lyrics_window.py

import sys
import os
import winreg
import json
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt, QPoint, pyqtSlot, QTimer
from PyQt6.QtWidgets import (QWidget, QSystemTrayIcon, 
                               QMenu, QApplication, QTextEdit, QVBoxLayout, QHBoxLayout, QPushButton, QLabel)
from PyQt6.QtGui import (QFont, QColor, QWheelEvent, QMouseEvent, QPainter, 
                         QBrush, QPen, QFontMetrics, QIcon, QAction)
from spotify_thread import SpotifyThread
import config
import time

# --- Constantes --- (Movidas de main.py)
APP_NAME = "LetrasPIP"
RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class LogWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Logs - LetrasPIP")
        self.setGeometry(200, 200, 600, 400)
        self.setWindowFlags(Qt.WindowType.Window)
        
        layout = QVBoxLayout()
        
        # Botões de controle
        button_layout = QHBoxLayout()
        self.clear_button = QPushButton("Limpar Logs")
        self.save_button = QPushButton("Salvar Logs")
        self.close_button = QPushButton("Fechar")
        
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.save_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        # Área de logs
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        
        layout.addLayout(button_layout)
        layout.addWidget(self.log_text)
        
        self.setLayout(layout)
        
        # Conectar botões
        self.clear_button.clicked.connect(self.clear_logs)
        self.save_button.clicked.connect(self.save_logs)
        self.close_button.clicked.connect(self.hide)
        
        self.logs = []
    
    def add_log(self, message):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        self.log_text.append(log_entry)
        
        # Auto-scroll para o final
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_logs(self):
        self.logs.clear()
        self.log_text.clear()
    
    def save_logs(self):
        from datetime import datetime
        filename = f"letraspip_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.logs))
            self.add_log(f"Logs salvos em: {filename}")
        except Exception as e:
            self.add_log(f"Erro ao salvar logs: {e}")

class LyricsWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.parsed_lyrics, self.current_line_index, self.manual_scroll_offset = [], -1, 0
        self.text_content, self._drag_pos = "Iniciando...", None
        self.user_has_scrolled = False
        self.scroll_snap_back_timer = QTimer(self)
        self.scroll_snap_back_timer.setSingleShot(True)
        self.scroll_snap_back_timer.setInterval(3000)
        self.scroll_snap_back_timer.timeout.connect(self.enable_snap_back)
        self.initial_label_hidden = False
        self.sync_offset = 0  # Offset de sincronização só aqui!
        
        # Sistema de logs
        self.log_window = LogWindow()
        self.log_window.add_log("Inicializando LetrasPIP...")
        
        # Sistema de persistência de offset por faixa
        self.offset_cache_file = os.path.join(config.CACHE_DIR, "offset_cache.json")
        self.offset_cache = self.load_offset_cache()
        
        self.log_window.add_log(f"sync_offset inicializado para 0 em __init__")
        
        self.create_tray_icon()
        self.init_ui()
        self.spotify_thread = SpotifyThread(self)
        self.spotify_thread.lyrics_data_ready.connect(self.update_lyrics_data)
        self.spotify_thread.start()

    def load_offset_cache(self):
        """Carrega o cache de offsets por faixa"""
        try:
            if os.path.exists(self.offset_cache_file):
                with open(self.offset_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.log_window.add_log(f"Erro ao carregar cache de offsets: {e}")
        return {}
    
    def save_offset_cache(self):
        """Salva o cache de offsets por faixa"""
        try:
            with open(self.offset_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.offset_cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log_window.add_log(f"Erro ao salvar cache de offsets: {e}")
    
    def get_track_key(self, artist, title):
        """Gera uma chave única para a faixa"""
        return f"{artist} - {title}".lower()
    
    def get_cached_offset(self, artist, title):
        """Obtém o offset salvo para uma faixa específica"""
        track_key = self.get_track_key(artist, title)
        return self.offset_cache.get(track_key, 0)
    
    def save_track_offset(self, artist, title, offset):
        """Salva o offset para uma faixa específica"""
        track_key = self.get_track_key(artist, title)
        self.offset_cache[track_key] = offset
        self.save_offset_cache()
        self.log_window.add_log(f"Offset salvo para '{track_key}': {offset}ms")

    def create_tray_icon(self):
        # 1. Cria o ícone e o menu
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        self.tray_icon.setIcon(QtGui.QIcon(resource_path('icon.ico')))
        self.tray_icon.setToolTip("LetrasPIP Spotify")
        self.tray_menu = QtWidgets.QMenu(self) # Passa 'self' como pai

        # 2. Cria as ações do menu como variáveis de instância
        self.logout_action = QAction("Sair da Conta", self)
        self.quit_action = QAction("Sair do Aplicativo", self)

        # 3. Adiciona as ações ao menu
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.logout_action)
        self.tray_menu.addAction(self.quit_action)

        # Ações de Sincronia
        self.tray_menu.addSeparator()
        self.increase_sync_action = QAction("Adiantar letra (+0.5s)", self)
        self.decrease_sync_action = QAction("Atrasar letra (-0.5s)", self)
        self.sync_status_action = QAction(f"Ajuste: {getattr(self, 'sync_offset', 0) / 1000:.1f}s", self)
        self.sync_status_action.setEnabled(False)
        self.tray_menu.addAction(self.increase_sync_action)
        self.tray_menu.addAction(self.decrease_sync_action)
        self.tray_menu.addAction(self.sync_status_action)

        self.tray_menu.addSeparator()
        self.reset_position_action = QAction("Centralizar letra", self)
        self.tray_menu.addAction(self.reset_position_action)
        
        # Ações de diagnóstico
        self.tray_menu.addSeparator()
        self.show_logs_action = QAction("Mostrar Logs", self)
        self.reset_offset_action = QAction("Resetar Offset", self)
        self.tray_menu.addAction(self.show_logs_action)
        self.tray_menu.addAction(self.reset_offset_action)

        # 4. Define o menu como o menu de contexto (o que abre com o botão direito)
        self.tray_icon.setContextMenu(self.tray_menu)

        # 5. Conecta as ações às suas funções
        self.quit_action.triggered.connect(QtWidgets.QApplication.instance().quit)
        self.increase_sync_action.triggered.connect(self.increase_sync)
        self.decrease_sync_action.triggered.connect(self.decrease_sync)
        self.reset_position_action.triggered.connect(self.reset_lyrics_position)
        self.show_logs_action.triggered.connect(self.show_logs)
        self.reset_offset_action.triggered.connect(self.reset_offset)

        # 6. Mostra o ícone
        self.tray_icon.show()

    def logout(self):
        """Para a thread do Spotify, deleta o cache e fecha o aplicativo."""
        try:
            # 1. Sinaliza para a thread parar
            self.spotify_thread.stop()
            # 2. Espera a thread realmente terminar (importante para liberar o arquivo)
            self.spotify_thread.wait(5000) # Espera até 5s

            # 3. Agora, com a thread parada, remove o cache
            if os.path.exists(config.CACHE_FILE):
                os.remove(config.CACHE_FILE)

        except Exception as e:
            # Em caso de erro, não fazemos nada barulhento, apenas logamos no console
            print(f"Erro silencioso durante o logout: {e}")
        finally:
            # 4. Fecha o aplicativo, aconteça o que acontecer
            QtWidgets.QApplication.instance().quit()

    def closeEvent(self, event):
        self.hide()
        event.ignore()

    def init_ui(self):
        self.setWindowIcon(QIcon(resource_path('icon.ico')))
        self.setWindowTitle('Letras PIP Spotify')
        self.setGeometry(100, 100, 400, 250)
        # Remover temporariamente FramelessWindowHint para debug de exibição
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        # Centralizar e garantir exibição
        screen = QtWidgets.QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.center() - self.rect().center())
        self.show()


    def increase_sync(self):
        self.sync_offset += 500
        self.log_window.add_log(f"sync_offset alterado para {self.sync_offset} em increase_sync")
        self._user_adjusted_sync = True
        self.log_window.add_log(f"_user_adjusted_sync alterado para True em increase_sync")
        self.log_window.add_log(f"Ajuste manual: increase_sync: sync_offset={self.sync_offset}")
        
        # Salva o offset para a faixa atual
        if hasattr(self, 'current_artist') and hasattr(self, 'current_song_title'):
            self.save_track_offset(self.current_artist, self.current_song_title, self.sync_offset)
        
        self.update_sync_label()
        self.update()

    def decrease_sync(self):
        self.sync_offset -= 500
        self.log_window.add_log(f"sync_offset alterado para {self.sync_offset} em decrease_sync")
        self._user_adjusted_sync = True
        self.log_window.add_log(f"_user_adjusted_sync alterado para True em decrease_sync")
        self.log_window.add_log(f"Ajuste manual: decrease_sync: sync_offset={self.sync_offset}")
        
        # Salva o offset para a faixa atual
        if hasattr(self, 'current_artist') and hasattr(self, 'current_song_title'):
            self.save_track_offset(self.current_artist, self.current_song_title, self.sync_offset)
        
        self.update_sync_label()
        self.update()

    def reset_lyrics_position(self):
        """Centraliza a janela no monitor principal e centraliza a letra na tela."""
        self.manual_scroll_offset = 0
        self.user_has_scrolled = False
        # Centraliza a janela no monitor principal
        screen = QtWidgets.QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())
        self.update()

    def update_sync_label(self):
        self.sync_status_action.setText(f"Ajuste: {self.sync_offset / 1000:.1f}s")

    def enable_snap_back(self):
        self.user_has_scrolled = False
        self.manual_scroll_offset = 0
        self._user_adjusted_sync = False
        self.log_window.add_log(f"_user_adjusted_sync alterado para False em enable_snap_back")
        self.update()

    def show_logs(self):
        """Mostra a janela de logs"""
        self.log_window.show()
        self.log_window.raise_()
        self.log_window.activateWindow()
    
    def reset_offset(self):
        """Reseta o offset para a faixa atual"""
        if hasattr(self, 'current_artist') and hasattr(self, 'current_song_title'):
            track_key = self.get_track_key(self.current_artist, self.current_song_title)
            self.sync_offset = 0
            self._user_adjusted_sync = False
            self.save_track_offset(self.current_artist, self.current_song_title, 0)
            self.log_window.add_log(f"Offset resetado para '{track_key}'")
            self.update_sync_label()
        self.update()

    @pyqtSlot(dict)
    def update_lyrics_data(self, data):
        # Inicializa flag de ajuste manual se não existir
        if not hasattr(self, '_user_adjusted_sync'):
            self._user_adjusted_sync = False
        
        # Calcula o progresso efetivo com o offset aplicado
        progress_ms = data.get('progress', 0)
        progress_with_offset = progress_ms + self.sync_offset
        
        # Verifica se há offset em cache para carregar
        if 'cached_offset' in data:
            cached_offset = data['cached_offset']
            self.sync_offset = cached_offset
            self._user_adjusted_sync = True
            self.log_window.add_log(f"Offset em cache carregado: {cached_offset}ms")
            self.update_sync_label()
            progress_with_offset = progress_ms + self.sync_offset

        # LOG EXTRA PARA DIAGNÓSTICO
        print("[DEBUG] update_lyrics_data chamada")
        print(f"[DEBUG] Payload recebido: {data}")
        # Detecta se o payload forneceu novos dados de letra ou apenas progresso
        has_parsed = 'parsed' in data
        has_text = 'text' in data

        new_parsed_lyrics = data.get('parsed') if has_parsed else None
        new_text = data.get('text') if has_text else None

        # --- INÍCIO DA LÓGICA ROBUSTA ---
        # Caso o payload contenha chave 'parsed'
        if has_parsed:
            if not new_parsed_lyrics:
                # Payload indicou que não há letras sincronizadas
                if new_text == "Nenhuma música tocando..." and self.text_content == new_text:
                    return
                self.text_content = new_text if new_text is not None else self.text_content
                self.current_line_index = -1
                self.parsed_lyrics = []
                self.update()
                return
            # Se há letras sincronizadas, atualiza a UI com a sincronização
            if new_parsed_lyrics is not None and self.parsed_lyrics != new_parsed_lyrics:
                self.log_window.add_log("=== RELOAD DE LETRAS SINCRONIZADAS DETECTADO ===")
                self.log_window.add_log(f"parsed_lyrics antigo: {[t for t, *_ in getattr(self, 'parsed_lyrics', [])]}")
                self.parsed_lyrics = new_parsed_lyrics

        # Atualiza o índice da linha atual apenas se houver letras sincronizadas
        if self.parsed_lyrics:
            new_current_line_index = -1
            bloco_log = ''
            if progress_with_offset < self.parsed_lyrics[0][0]:
                new_current_line_index = 0
                bloco_log = f"(start={self.parsed_lyrics[0][0]}, end={self.parsed_lyrics[0][1]}, text='{self.parsed_lyrics[0][2]}')"
            else:
                # Procura bloco cujo intervalo cobre o tempo atual
                for i, (start, end, text) in enumerate(self.parsed_lyrics):
                    if start <= progress_with_offset < end:
                        new_current_line_index = i
                        bloco_log = f"(start={start}, end={end}, text='{text}')"
                        break
                # Se não encontrou, mantém o último verso válido
                if new_current_line_index == -1:
                    new_current_line_index = len(self.parsed_lyrics) - 1
                    last = self.parsed_lyrics[new_current_line_index]
                    bloco_log = f"(start={last[0]}, end={last[1]}, text='{last[2]}') [LAST]"
            # Log detalhado do bloco selecionado
            new_line_text = self.parsed_lyrics[new_current_line_index][2] if 0 <= new_current_line_index < len(self.parsed_lyrics) else None
            self.log_window.add_log(f"[SYNC] progress={progress_ms}ms | offset={self.sync_offset}ms | progress+offset={progress_with_offset}ms | idx={new_current_line_index} | bloco={bloco_log}")
            # Loga os intervalos de todos os blocos (resumido)
            blocos_resumidos = ', '.join([f"({s}-{e})" for s,e,_ in self.parsed_lyrics])
            self.log_window.add_log(f"[SYNC] Blocos: {blocos_resumidos}")
            if new_current_line_index != self.current_line_index:
                self.current_line_index = new_current_line_index
                self.user_has_scrolled = False
                self.update()
            else:
                self.update()
        else:
            # Não há parsed_lyrics: exibe texto puro centralizado
            if new_text:
                self.text_content = new_text
                self.current_line_index = -1
                self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(0, 0, 0, 1)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))  # Fundo totalmente transparente
        painter.drawRoundedRect(self.rect(), 10, 10)
        if not self.parsed_lyrics:
            painter.setFont(QFont('Arial', 14))
            painter.setPen(QPen(QColor(255, 255, 255, 200)))
            rect = self.rect().adjusted(32, 0, -32, 0)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.text_content)
            return
        line_height = 48  # Mais espaçamento vertical
        total_lines_to_display = 5
        view_center_y = self.height() // 2
        center_index = self.current_line_index if not self.user_has_scrolled else max(0, min(self.current_line_index + self.manual_scroll_offset, len(self.parsed_lyrics) - 1))
        start_index = max(0, center_index - (total_lines_to_display // 2))
        end_index = min(len(self.parsed_lyrics), start_index + total_lines_to_display)
        for i in range(start_index, end_index):
            start, end, text = self.parsed_lyrics[i]
            y = view_center_y + (i - center_index) * line_height
            if i == center_index:
                font_size = 24  # Fonte máxima menor
                padding = 48    # Mais padding lateral
                metrics = QFontMetrics(QFont('Arial', font_size, QFont.Weight.Bold))
                while metrics.horizontalAdvance(text) > self.width() - 2 * padding and font_size > 16:
                    font_size -= 2
                    metrics = QFontMetrics(QFont('Arial', font_size, QFont.Weight.Bold))
                painter.setFont(QFont('Arial', font_size, QFont.Weight.Bold))
                painter.setPen(QPen(QColor(255, 255, 255, 255)))
            else:
                painter.setFont(QFont('Arial', 18))
                painter.setPen(QPen(QColor(255, 255, 255, 110)))
            rect = self.rect().adjusted(padding if i == center_index else 0, y - view_center_y, -(padding if i == center_index else 0), y - view_center_y)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)
        # Estrutura pronta para cor baseada na capa do álbum (a ser implementado)

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
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
        event.accept()

