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
        
        import traceback
        self.log_window.add_log(f"sync_offset inicializado para 0 em __init__")
        traceback.print_stack(limit=2)
        
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
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

    def increase_sync(self):
        self.sync_offset += 500
        import traceback
        self.log_window.add_log(f"sync_offset alterado para {self.sync_offset} em increase_sync")
        traceback.print_stack(limit=2)
        self._user_adjusted_sync = True
        import traceback
        self.log_window.add_log(f"_user_adjusted_sync alterado para True em increase_sync")
        traceback.print_stack(limit=2)
        self.log_window.add_log(f"Ajuste manual: increase_sync: sync_offset={self.sync_offset}")
        
        # Salva o offset para a faixa atual
        if hasattr(self, 'current_artist') and hasattr(self, 'current_song_title'):
            self.save_track_offset(self.current_artist, self.current_song_title, self.sync_offset)
        
        self.update_sync_label()
        self.update()

    def decrease_sync(self):
        self.sync_offset -= 500
        import traceback
        self.log_window.add_log(f"sync_offset alterado para {self.sync_offset} em decrease_sync")
        traceback.print_stack(limit=2)
        self._user_adjusted_sync = True
        import traceback
        self.log_window.add_log(f"_user_adjusted_sync alterado para True em decrease_sync")
        traceback.print_stack(limit=2)
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
        import traceback
        self.log_window.add_log(f"_user_adjusted_sync alterado para False em enable_snap_back")
        traceback.print_stack(limit=2)
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
            
        # Verifica se há offset em cache para carregar
        if 'cached_offset' in data:
            cached_offset = data['cached_offset']
            self.sync_offset = cached_offset
            self._user_adjusted_sync = True  # Marca como ajustado pelo usuário
            self.log_window.add_log(f"Offset em cache carregado: {cached_offset}ms")
            self.update_sync_label()
            
        # --- Salva índice/tempo da linha ativa antes do reload ---
        if hasattr(self, 'parsed_lyrics') and self.parsed_lyrics and getattr(self, 'current_line_index', -1) >= 0:
            self._last_line_index = self.current_line_index
            self._last_line_time = self.parsed_lyrics[self.current_line_index][0]
        else:
            self._last_line_index = None
            self._last_line_time = None

        progress_ms = data.get('progress', 0)
        new_parsed_lyrics = data.get('parsed', [])
        new_text = data.get('text', '')
        
        # Reseta flag ao trocar de música (parsed_lyrics antigo vazio e novo não vazio)
        if not getattr(self, 'parsed_lyrics', []) and new_parsed_lyrics:
            self._user_adjusted_sync = False
            import traceback
            self.log_window.add_log(f"_user_adjusted_sync alterado para False em troca de música (parsed_lyrics reload)")
            traceback.print_stack(limit=2)

        # Se não há letras sincronizadas, mostra o texto diretamente
        if not new_parsed_lyrics:
            if new_text == "Nenhuma música tocando..." and self.text_content == new_text:
                return
            self.text_content = new_text
            self.current_line_index = -1
            self.parsed_lyrics = []
            self.update()
            return

        # Se há letras sincronizadas, atualiza a UI com a sincronização
        if self.parsed_lyrics != new_parsed_lyrics:
            self.log_window.add_log("=== RELOAD DE LETRAS SINCRONIZADAS DETECTADO ===")
            self.log_window.add_log(f"parsed_lyrics antigo: {[t for t, _ in getattr(self, 'parsed_lyrics', [])]}")
            self.log_window.add_log(f"parsed_lyrics novo:   {[t for t, _ in new_parsed_lyrics]}")
            
            # --- Ajuste automático do offset após reload para manter a linha ativa (busca pelo tempo mais próximo) ---
            if not self._user_adjusted_sync and hasattr(self, '_last_line_time') and self._last_line_time is not None and new_parsed_lyrics:
                self.log_window.add_log(f"Antes do ajuste: sync_offset={self.sync_offset}, last_line_time={self._last_line_time}")
                tempos = [t for t, _ in new_parsed_lyrics]
                closest_idx = min(range(len(tempos)), key=lambda i: abs(tempos[i] - self._last_line_time))
                new_line_time = tempos[closest_idx]
                self.log_window.add_log(f"Novo tempo encontrado na letra: {new_line_time}, progresso puro recebido: {data.get('progress', 0)}")
                self.sync_offset += (new_line_time - data.get('progress', 0))
                import traceback
                self.log_window.add_log(f"sync_offset alterado para {self.sync_offset} em ajuste automático de linha")
                traceback.print_stack(limit=2)
                self.log_window.add_log(f"Depois do ajuste: sync_offset={self.sync_offset}")
                progress_ms = data.get('progress', 0) + self.sync_offset
            self.parsed_lyrics = new_parsed_lyrics
            self.manual_scroll_offset = 0
            font = QFont('Arial', 22)
            font.setBold(True)
            fm = QFontMetrics(font)
            max_width = max(fm.horizontalAdvance(line) for _, line in self.parsed_lyrics)
            self.resize(max(max_width + 40, 400), self.height())
            self.text_content = ""

        # Atualiza o índice da linha atual apenas se houver letras sincronizadas
        if self.parsed_lyrics:
            self.log_window.add_log(f"progress_ms: {progress_ms}, tempos das linhas: {[t for t, _ in self.parsed_lyrics]}")
            new_current_line_index = -1
            # Se o progresso é menor que a primeira linha, destaca a primeira linha
            if progress_ms + self.sync_offset < self.parsed_lyrics[0][0]:
                new_current_line_index = 0
            else:
                for i, (line_time, text) in enumerate(self.parsed_lyrics):
                    progresso_efetivo = progress_ms + self.sync_offset
                    # LOG DE DIAGNÓSTICO: monitora a transição para a linha 15
                    if i == 15:
                        self.log_window.add_log(f"[DIAGNÓSTICO DA FALHA] Alvo: Linha {i} ('{text}') | Timestamp da linha alvo: {line_time} | progress_ms: {progress_ms} | sync_offset: {self.sync_offset} | Progresso Efetivo: {progresso_efetivo} < {line_time} ?")
                    if progresso_efetivo >= line_time and (i == len(self.parsed_lyrics)-1 or progresso_efetivo < self.parsed_lyrics[i+1][0]):
                        new_current_line_index = i
                        break
            # Logging detalhado para diagnóstico
            current_line_text = self.parsed_lyrics[self.current_line_index][1] if 0 <= self.current_line_index < len(self.parsed_lyrics) else None
            new_line_text = self.parsed_lyrics[new_current_line_index][1] if 0 <= new_current_line_index < len(self.parsed_lyrics) else None
            # Log extra: tempo até o próximo verso e desde o início do atual
            if 0 <= new_current_line_index < len(self.parsed_lyrics):
                current_line_time = self.parsed_lyrics[new_current_line_index][0]
                next_line_time = self.parsed_lyrics[new_current_line_index+1][0] if new_current_line_index+1 < len(self.parsed_lyrics) else None
                delta_next = (next_line_time - progress_ms) if next_line_time is not None else None
                delta_current = progress_ms - current_line_time
                self.log_window.add_log(f"[SYNC DETAIL] Linha atual: {new_current_line_index} ('{new_line_text}') | Desde início: {delta_current} ms | Até próximo: {delta_next} ms")
            self.log_window.add_log(f"[SYNC DEBUG] progress={data.get('progress', 0)}, sync_offset={self.sync_offset}, progress_ms={progress_ms}, _user_adjusted_sync={getattr(self, '_user_adjusted_sync', False)}")
            self.log_window.add_log(f"[SYNC DEBUG] current_line_index: {self.current_line_index} ('{current_line_text}') -> {new_current_line_index} ('{new_line_text}')")
            if new_current_line_index != self.current_line_index:
                # --- SUAVIZAÇÃO: limitar avanço para no máximo 1 linha por ciclo ---
                if self.current_line_index is not None and self.current_line_index >= 0:
                    if new_current_line_index > self.current_line_index + 1:
                        new_current_line_index = self.current_line_index + 1
                    elif new_current_line_index < self.current_line_index - 1:
                        new_current_line_index = self.current_line_index - 1
                # --- FIM DA SUAVIZAÇÃO ---
                self.current_line_index = new_current_line_index
                self.user_has_scrolled = False  # Volta a centralizar ao mudar de verso
                self.update()
            else:
                self.update()  # Força repaint mesmo se não mudou

            # --- SUAVIZAÇÃO AVANÇADA: delay mínimo entre linhas após grande salto ---
            # Parâmetros
            DELAY_MINIMO_MS = 1000  # 1 segundo mínimo por linha
            GRANDE_SALTO_MS = 5000  # Considera salto se ficou mais de 5s parado
            if not hasattr(self, '_suavizando_catchup'):
                self._suavizando_catchup = False
            if not hasattr(self, '_ultimo_avanco_ms'):
                self._ultimo_avanco_ms = 0
            agora_ms = int(time.time() * 1000)
            # Detecta grande salto
            if hasattr(self, '_last_line_time') and self._last_line_time is not None and current_line_time - self._last_line_time > GRANDE_SALTO_MS:
                self._suavizando_catchup = True
                self._catchup_linhas_restantes = new_current_line_index - self.current_line_index if new_current_line_index > self.current_line_index else 0
                self._ultimo_avanco_ms = agora_ms
            # Se está suavizando catchup, só avança se passou o delay mínimo
            if self._suavizando_catchup and new_current_line_index > self.current_line_index:
                if agora_ms - self._ultimo_avanco_ms < DELAY_MINIMO_MS:
                    new_current_line_index = self.current_line_index  # Segura na linha atual
                else:
                    self._ultimo_avanco_ms = agora_ms
                    self._catchup_linhas_restantes -= 1
                    if self._catchup_linhas_restantes <= 0:
                        self._suavizando_catchup = False
            # --- FIM DA SUAVIZAÇÃO AVANÇADA ---

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setBrush(QBrush(QColor(0, 0, 0, 1)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 10, 10)
        painter.setPen(QPen(Qt.GlobalColor.white))
        
        if not self.parsed_lyrics:
            painter.setFont(QFont('Arial', 12))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.text_content)
            return
        
        line_height = 35
        total_lines_to_display = 5
        view_center_y = self.height() // 2
        # Centraliza sempre o verso atual, exceto se o usuário rolou
        center_index = self.current_line_index if not self.user_has_scrolled else max(0, min(self.current_line_index + self.manual_scroll_offset, len(self.parsed_lyrics) - 1))
        start_index = max(0, center_index - (total_lines_to_display // 2))
        end_index = min(len(self.parsed_lyrics), start_index + total_lines_to_display)
        
        for i in range(start_index, end_index):
            _, line_text = self.parsed_lyrics[i]
            is_current_line = (i == self.current_line_index)
            font = QFont('Arial')
            font.setBold(is_current_line)
            font.setPixelSize(22 if is_current_line else 18)
            painter.setFont(font)
            
            distance_from_center = i - center_index
            opacity = max(0, 1.0 - (abs(distance_from_center) * 0.25))
            color = QColor(220, 220, 220)
            if is_current_line:
                color = QColor(255, 255, 255)
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

