# lyrics_window.py

import sys
import os
import winreg
import json
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt, QPoint, pyqtSlot, QTimer, QRect
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
        # Ativar fundo transparente e modo frameless
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        # Centralizar e garantir exibição
        screen = QtWidgets.QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.center() - self.rect().center())
        self.show()


    def increase_sync(self):
        print(f"[DEBUG] increase_sync chamado - offset atual: {self.sync_offset}")
        self.sync_offset += 500
        self.log_window.add_log(f"sync_offset alterado para {self.sync_offset} em increase_sync")
        self._user_adjusted_sync = True
        self.log_window.add_log(f"_user_adjusted_sync alterado para True em increase_sync")
        self.log_window.add_log(f"Ajuste manual: increase_sync: sync_offset={self.sync_offset}")
        print(f"[DEBUG] increase_sync finalizado - novo offset: {self.sync_offset}")
        
        # Salva o offset para a faixa atual
        if hasattr(self, 'current_artist') and hasattr(self, 'current_song_title'):
            self.save_track_offset(self.current_artist, self.current_song_title, self.sync_offset)
        
        self.update_sync_label()
        self.update()

    def decrease_sync(self):
        print(f"[DEBUG] decrease_sync chamado - offset atual: {self.sync_offset}")
        self.sync_offset -= 500
        self.log_window.add_log(f"sync_offset alterado para {self.sync_offset} em decrease_sync")
        self._user_adjusted_sync = True
        self.log_window.add_log(f"_user_adjusted_sync alterado para True em decrease_sync")
        self.log_window.add_log(f"Ajuste manual: decrease_sync: sync_offset={self.sync_offset}")
        print(f"[DEBUG] decrease_sync finalizado - novo offset: {self.sync_offset}")
        
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
        print(f"[DEBUG] [RESET_OFFSET] chamado - offset atual: {self.sync_offset}")
        self.log_window.add_log(f"[RESET_OFFSET] chamado - offset atual: {self.sync_offset}")
        if hasattr(self, 'current_artist') and hasattr(self, 'current_song_title'):
            track_key = self.get_track_key(self.current_artist, self.current_song_title)
            self.sync_offset = 0
            self._user_adjusted_sync = True  # Impede sobrescrita pelo cache
            self.offset_cache[track_key] = 0
            self.save_offset_cache()
            self.log_window.add_log(f"[RESET_OFFSET] Offset resetado para '{track_key}': 0ms")
            self.update_sync_label()
            self.update()
        print(f"[DEBUG] [RESET_OFFSET] finalizado - offset atual: {self.sync_offset}")

    @pyqtSlot(dict)
    def update_lyrics_data(self, data):
        print(f"[DEBUG] [UPDATE_LYRICS_DATA] INÍCIO - sync_offset: {self.sync_offset}")
        self.log_window.add_log(f"[UPDATE_LYRICS_DATA] INÍCIO - sync_offset: {self.sync_offset}")
        # Inicializa flag de ajuste manual se não existir
        if not hasattr(self, '_user_adjusted_sync'):
            self._user_adjusted_sync = False
        
        # Extrai informações da faixa atual se disponíveis
        if 'artist' in data and 'title' in data:
            self.current_artist = data['artist']
            self.current_song_title = data['title']
            self.log_window.add_log(f"Faixa atual atualizada: {self.current_artist} - {self.current_song_title}")
        
        # Calcula o progresso efetivo com o offset aplicado
        progress_ms = data.get('progress', 0)
        progress_with_offset = progress_ms + self.sync_offset
        print(f'[DEBUG] === APLICAÇÃO DO OFFSET ===')
        print(f'[DEBUG] Progress original: {progress_ms}ms')
        print(f'[DEBUG] Offset atual: {self.sync_offset}ms')
        print(f'[DEBUG] Progress com offset: {progress_with_offset}ms')
        print(f'[DEBUG] Diferença aplicada: {progress_with_offset - progress_ms}ms')
        
        # Verifica se há offset em cache para carregar
        if 'cached_offset' in data:
            cached_offset = data['cached_offset']
            print(f"[DEBUG] [UPDATE_LYRICS_DATA] RECEBEU cached_offset: {cached_offset} | _user_adjusted_sync={self._user_adjusted_sync}")
            self.log_window.add_log(f"[UPDATE_LYRICS_DATA] RECEBEU cached_offset: {cached_offset} | _user_adjusted_sync={self._user_adjusted_sync}")
            # Só aplica o cached_offset se for diferente do offset atual
            # Isso evita que o offset seja resetado incorretamente
            if self.sync_offset != cached_offset:
                print(f"[DEBUG] [UPDATE_LYRICS_DATA] VAI APLICAR cached_offset: {cached_offset}")
                self.log_window.add_log(f"[UPDATE_LYRICS_DATA] VAI APLICAR cached_offset: {cached_offset}")
                self.sync_offset = cached_offset
                self.log_window.add_log(f"Offset em cache carregado: {cached_offset}ms")
                self.update_sync_label()
                # ATUALIZA O PROGRESSO COM O NOVO OFFSET
                progress_with_offset = progress_ms + self.sync_offset
                print(f'[DEBUG] === REAPLICAÇÃO DO OFFSET APÓS CACHED ===')
                print(f'[DEBUG] Novo offset: {self.sync_offset}ms')
                print(f'[DEBUG] Progress com novo offset: {progress_with_offset}ms')
        print(f"[DEBUG] [UPDATE_LYRICS_DATA] FIM - sync_offset: {self.sync_offset}")
        self.log_window.add_log(f"[UPDATE_LYRICS_DATA] FIM - sync_offset: {self.sync_offset}")
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
            print(f'[DEBUG] === SELEÇÃO DO VERSO ===')
            print(f'[DEBUG] Total de versos: {len(self.parsed_lyrics)}')
            new_current_line_index = -1
            bloco_log = ''
            if progress_with_offset < self.parsed_lyrics[0][0]:
                new_current_line_index = 0
                bloco_log = f"(start={self.parsed_lyrics[0][0]}, end={self.parsed_lyrics[0][1]}, text='{self.parsed_lyrics[0][2]}')"
                print(f'[DEBUG] Antes do primeiro verso - selecionando verso 0')
            else:
                # Procura bloco cujo intervalo cobre o tempo atual (pega o ÚLTIMO, não o primeiro)
                print(f'[DEBUG] Procurando verso para progress_with_offset={progress_with_offset}ms')
                for i, (start, end, text) in enumerate(self.parsed_lyrics):
                    print(f'[DEBUG] Verso {i}: {start}ms-{end}ms | "{text[:30]}..." | Match: {start <= progress_with_offset < end}')
                    if start <= progress_with_offset < end:
                        new_current_line_index = i  # NÃO faz break, pega o último!
                        bloco_log = f"(start={start}, end={end}, text='{text}')"
                if new_current_line_index != -1:
                    print(f'[DEBUG] ✓ VERSO ENCONTRADO: {new_current_line_index} | {self.parsed_lyrics[new_current_line_index][0]}ms-{self.parsed_lyrics[new_current_line_index][1]}ms')
                # Se não encontrou, mantém o último verso válido
                if new_current_line_index == -1:
                    new_current_line_index = len(self.parsed_lyrics) - 1
                    last = self.parsed_lyrics[new_current_line_index]
                    bloco_log = f"(start={last[0]}, end={last[1]}, text='{last[2]}') [LAST]"
                    print(f'[DEBUG] ⚠ Nenhum verso encontrado - usando último: {new_current_line_index}')
            # Log detalhado do bloco selecionado
            new_line_text = self.parsed_lyrics[new_current_line_index][2] if 0 <= new_current_line_index < len(self.parsed_lyrics) else None
            self.log_window.add_log(f"[SYNC] progress={progress_ms}ms | offset={self.sync_offset}ms | progress+offset={progress_with_offset}ms | idx={new_current_line_index} | bloco={bloco_log}")
            print(f"[DEBUG] Verso selecionado: idx={new_current_line_index} | texto='{new_line_text}' | progress_with_offset={progress_with_offset}ms")
            # Loga os intervalos de todos os blocos (resumido)
            blocos_resumidos = ', '.join([f"({s}-{e})" for s,e,_ in self.parsed_lyrics])
            self.log_window.add_log(f"[SYNC] Blocos: {blocos_resumidos}")
            if new_current_line_index != self.current_line_index:
                print(f"[DEBUG] MUDANÇA DE VERSO: {self.current_line_index} -> {new_current_line_index}")
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
        
        # Fundo transparente
        painter.setBrush(QBrush(QColor(0, 0, 0, 120)))
        painter.setPen(QPen(QColor(0, 0, 0, 0)))
        painter.drawRect(self.rect())
        
        # Se não há letras, mostrar mensagem
        if not self.parsed_lyrics:
            msg = self.text_content if self.text_content else "Nenhuma letra disponível"
            painter.setFont(QFont('Arial', 16, QFont.Weight.Normal))
            painter.setPen(QPen(QColor(255, 255, 255, 220)))
            rect = self.rect().adjusted(32, 0, -32, 0)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, msg)
            return
        
        # Calcular alturas reais de cada verso
        padding = 32  # Reduzir padding para mais espaço
        verse_spacing = 15  # Espaçamento entre versos
        
        # --- Seleção dos versos a serem exibidos ---
        context_above = 2
        context_below = 2
        num_verses = len(self.parsed_lyrics)
        
        center_index = self.current_line_index if not self.user_has_scrolled else max(0, min(self.current_line_index + self.manual_scroll_offset, num_verses - 1))
        
        # Garante que sempre haja pelo menos 2 acima e 2 abaixo, se possível
        start_index = max(0, center_index - context_above)
        end_index = min(num_verses, center_index + context_below + 1)
        
        # Se não couber tudo na janela, reduz o contexto, mas nunca menos que o central
        while True:
            # Calcular alturas reais
            heights = []
            for i in range(start_index, end_index):
                _, _, text = self.parsed_lyrics[i]
                
                if i == center_index:
                    font = QFont('Arial', 26, QFont.Weight.Bold)
                    metrics = QFontMetrics(font)
                else:
                    font = QFont('Arial', 18, QFont.Weight.Normal)
                    metrics = QFontMetrics(font)
                rect = QRect(padding, 0, self.width() - 2*padding, 0)
                text_rect = metrics.boundingRect(rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)
                heights.append(max(text_rect.height() + 15, 40))
            total_content_height = sum(heights) + (len(heights) - 1) * verse_spacing
            if total_content_height <= self.height() - 60 or (start_index == center_index and end_index == center_index+1):
                break
            # Reduz contexto simetricamente
            if end_index - start_index > 1:
                if (end_index - 1) - center_index > center_index - start_index:
                    end_index -= 1
                else:
                    start_index += 1
            else:
                break
        
        # NOVA LÓGICA: Centralizar o verso em destaque especificamente
        center_verse_idx = center_index - start_index  # Índice local do verso central
        
        if center_verse_idx >= 0 and center_verse_idx < len(heights):
            # Calcular altura total dos versos ANTES do verso central
            height_before_center = 0
            for i in range(center_verse_idx):
                height_before_center += heights[i] + verse_spacing
            
            # Posicionar o verso central no meio da janela
            center_verse_height = heights[center_verse_idx]
            window_center_y = self.height() // 2
            center_verse_y = window_center_y - (center_verse_height // 2)
            
            # Calcular posição inicial considerando os versos anteriores
            start_y = max(30, center_verse_y - height_before_center)
        else:
            # Fallback: centralizar todo o bloco
            total_content_height = sum(heights) + (len(heights) - 1) * verse_spacing
            start_y = max(30, (self.height() - total_content_height) // 2)
        
        current_y = start_y
        
        # Verificar se há clipping e ajustar se necessário
        total_content_height = sum(heights) + (len(heights) - 1) * verse_spacing
        if total_content_height > self.height() - 60:
            # Se o conteúdo é maior que a janela, ajustar para evitar clipping
            if center_verse_idx >= 0 and center_verse_idx < len(heights):
                # Garantir que o verso central fique visível
                max_start_y = self.height() - 30 - total_content_height
                start_y = min(start_y, max_start_y)
                start_y = max(30, start_y)  # Manter margem superior
                current_y = start_y
        
        for idx, i in enumerate(range(start_index, end_index)):
            _, _, text = self.parsed_lyrics[i]
            
            # Configurar fonte e cor
            if i == center_index:
                font = QFont('Arial', 26, QFont.Weight.Bold)  # Fonte maior para destaque
                color = QColor(255, 255, 255, 255)  # Branco total
            else:
                font = QFont('Arial', 18, QFont.Weight.Normal)
                color = QColor(255, 255, 255, 160)  # Mais suave para contexto
            
            painter.setFont(font)
            painter.setPen(QPen(color))
            
            # Criar retângulo para o verso
            verse_height = heights[idx]
            rect = QRect(padding, current_y, self.width() - 2*padding, verse_height)
            
            # Desenhar o texto centralizado
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)
            
            # Avançar para próximo verso
            current_y += verse_height + verse_spacing
        
        # Mostrar offset atual no canto inferior direito
        offset_str = f"Offset: {self.sync_offset/1000:.2f}s"
        painter.setFont(QFont('Arial', 12))
        painter.setPen(QPen(QColor(200, 200, 200, 180)))
        painter.drawText(self.rect().adjusted(0, 0, -12, -8), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, offset_str)

    def wheelEvent(self, event: QWheelEvent):
        if not self.parsed_lyrics:
            return
        print('[DEBUG] wheelEvent acionado')
        self.user_has_scrolled = True
        self.scroll_snap_back_timer.start()
        delta = -1 if event.angleDelta().y() > 0 else 1
        self.manual_scroll_offset += delta
        max_offset = len(self.parsed_lyrics) - 1 - self.current_line_index
        min_offset = -self.current_line_index
        self.manual_scroll_offset = max(min_offset, min(self.manual_scroll_offset, max_offset))
        print(f'[DEBUG] manual_scroll_offset: {self.manual_scroll_offset}')
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

    def reset_offset(self):
        """Reseta o offset para a faixa atual"""
        print(f"[DEBUG] [RESET_OFFSET] chamado - offset atual: {self.sync_offset}")
        self.log_window.add_log(f"[RESET_OFFSET] chamado - offset atual: {self.sync_offset}")
        if hasattr(self, 'current_artist') and hasattr(self, 'current_song_title'):
            track_key = self.get_track_key(self.current_artist, self.current_song_title)
            self.sync_offset = 0
            self._user_adjusted_sync = True  # Impede sobrescrita pelo cache
            self.offset_cache[track_key] = 0
            self.save_offset_cache()
            self.log_window.add_log(f"[RESET_OFFSET] Offset resetado para '{track_key}': 0ms")
            self.update_sync_label()
            self.update()
        print(f"[DEBUG] [RESET_OFFSET] finalizado - offset atual: {self.sync_offset}")

    @pyqtSlot(dict)
    def update_lyrics_data(self, data):
        print(f"[DEBUG] [UPDATE_LYRICS_DATA] INÍCIO - sync_offset: {self.sync_offset}")
        self.log_window.add_log(f"[UPDATE_LYRICS_DATA] INÍCIO - sync_offset: {self.sync_offset}")
        # Inicializa flag de ajuste manual se não existir
        if not hasattr(self, '_user_adjusted_sync'):
            self._user_adjusted_sync = False
        
        # Extrai informações da faixa atual se disponíveis
        if 'artist' in data and 'title' in data:
            self.current_artist = data['artist']
            self.current_song_title = data['title']
            self.log_window.add_log(f"Faixa atual atualizada: {self.current_artist} - {self.current_song_title}")
        
        # Calcula o progresso efetivo com o offset aplicado
        progress_ms = data.get('progress', 0)
        progress_with_offset = progress_ms + self.sync_offset
        print(f'[DEBUG] === APLICAÇÃO DO OFFSET ===')
        print(f'[DEBUG] Progress original: {progress_ms}ms')
        print(f'[DEBUG] Offset atual: {self.sync_offset}ms')
        print(f'[DEBUG] Progress com offset: {progress_with_offset}ms')
        print(f'[DEBUG] Diferença aplicada: {progress_with_offset - progress_ms}ms')
        
        # Verifica se há offset em cache para carregar
        if 'cached_offset' in data:
            cached_offset = data['cached_offset']
            print(f"[DEBUG] [UPDATE_LYRICS_DATA] RECEBEU cached_offset: {cached_offset} | _user_adjusted_sync={self._user_adjusted_sync}")
            self.log_window.add_log(f"[UPDATE_LYRICS_DATA] RECEBEU cached_offset: {cached_offset} | _user_adjusted_sync={self._user_adjusted_sync}")
            # Só aplica o cached_offset se for diferente do offset atual
            # Isso evita que o offset seja resetado incorretamente
            if self.sync_offset != cached_offset:
                print(f"[DEBUG] [UPDATE_LYRICS_DATA] VAI APLICAR cached_offset: {cached_offset}")
                self.log_window.add_log(f"[UPDATE_LYRICS_DATA] VAI APLICAR cached_offset: {cached_offset}")
                self.sync_offset = cached_offset
                self.log_window.add_log(f"Offset em cache carregado: {cached_offset}ms")
                self.update_sync_label()
                # ATUALIZA O PROGRESSO COM O NOVO OFFSET
                progress_with_offset = progress_ms + self.sync_offset
                print(f'[DEBUG] === REAPLICAÇÃO DO OFFSET APÓS CACHED ===')
                print(f'[DEBUG] Novo offset: {self.sync_offset}ms')
                print(f'[DEBUG] Progress com novo offset: {progress_with_offset}ms')
        print(f"[DEBUG] [UPDATE_LYRICS_DATA] FIM - sync_offset: {self.sync_offset}")
        self.log_window.add_log(f"[UPDATE_LYRICS_DATA] FIM - sync_offset: {self.sync_offset}")
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
            print(f'[DEBUG] === SELEÇÃO DO VERSO ===')
            print(f'[DEBUG] Total de versos: {len(self.parsed_lyrics)}')
            new_current_line_index = -1
            bloco_log = ''
            if progress_with_offset < self.parsed_lyrics[0][0]:
                new_current_line_index = 0
                bloco_log = f"(start={self.parsed_lyrics[0][0]}, end={self.parsed_lyrics[0][1]}, text='{self.parsed_lyrics[0][2]}')"
                print(f'[DEBUG] Antes do primeiro verso - selecionando verso 0')
            else:
                # Procura bloco cujo intervalo cobre o tempo atual (pega o ÚLTIMO, não o primeiro)
                print(f'[DEBUG] Procurando verso para progress_with_offset={progress_with_offset}ms')
                for i, (start, end, text) in enumerate(self.parsed_lyrics):
                    print(f'[DEBUG] Verso {i}: {start}ms-{end}ms | "{text[:30]}..." | Match: {start <= progress_with_offset < end}')
                    if start <= progress_with_offset < end:
                        new_current_line_index = i  # NÃO faz break, pega o último!
                        bloco_log = f"(start={start}, end={end}, text='{text}')"
                if new_current_line_index != -1:
                    print(f'[DEBUG] ✓ VERSO ENCONTRADO: {new_current_line_index} | {self.parsed_lyrics[new_current_line_index][0]}ms-{self.parsed_lyrics[new_current_line_index][1]}ms')
                # Se não encontrou, mantém o último verso válido
                if new_current_line_index == -1:
                    new_current_line_index = len(self.parsed_lyrics) - 1
                    last = self.parsed_lyrics[new_current_line_index]
                    bloco_log = f"(start={last[0]}, end={last[1]}, text='{last[2]}') [LAST]"
                    print(f'[DEBUG] ⚠ Nenhum verso encontrado - usando último: {new_current_line_index}')
            # Log detalhado do bloco selecionado
            new_line_text = self.parsed_lyrics[new_current_line_index][2] if 0 <= new_current_line_index < len(self.parsed_lyrics) else None
            self.log_window.add_log(f"[SYNC] progress={progress_ms}ms | offset={self.sync_offset}ms | progress+offset={progress_with_offset}ms | idx={new_current_line_index} | bloco={bloco_log}")
            print(f"[DEBUG] Verso selecionado: idx={new_current_line_index} | texto='{new_line_text}' | progress_with_offset={progress_with_offset}ms")
            # Loga os intervalos de todos os blocos (resumido)
            blocos_resumidos = ', '.join([f"({s}-{e})" for s,e,_ in self.parsed_lyrics])
            self.log_window.add_log(f"[SYNC] Blocos: {blocos_resumidos}")
            if new_current_line_index != self.current_line_index:
                print(f"[DEBUG] MUDANÇA DE VERSO: {self.current_line_index} -> {new_current_line_index}")
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
