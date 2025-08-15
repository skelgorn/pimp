# -*- coding: utf-8 -*-
"""
LetrasPIP - Correções Específicas
Resolve: sobreposição de texto + offset adaptativo por seção da música
"""

import re
import json
import os
import time
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, asdict
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QPainter, QFont, QColor, QPen, QBrush, QFontMetrics
from PyQt6.QtWidgets import QWidget

# ===== SISTEMA DE OFFSET ADAPTATIVO POR SEÇÃO =====

@dataclass
class SectionOffset:
    """Offset específico para uma seção da música"""
    start_time: int      # Início da seção em ms
    end_time: int        # Fim da seção em ms  
    offset: int          # Offset para esta seção
    confidence: float    # Confiança no offset (0-1)
    user_adjusted: bool  # Se foi ajustado pelo usuário

@dataclass
class AdaptiveOffsetData:
    """Dados de offset adaptativo por música"""
    track_key: str
    base_offset: int = 0
    sections: List[SectionOffset] = None
    last_updated: float = 0
    
    def __post_init__(self):
        if self.sections is None:
            self.sections = []

class AdaptiveOffsetManager:
    """Gerenciador de offset que se adapta por seções da música"""
    
    def __init__(self, cache_dir: str):
        self.cache_file = os.path.join(cache_dir, "adaptive_offset_cache.json")
        self.cache: Dict[str, AdaptiveOffsetData] = {}
        self.current_track: Optional[AdaptiveOffsetData] = None
        self.current_section_index = -1
        self.load_cache()
        
        # Configurações
        self.section_min_duration = 15000  # 15s mínimo por seção
        self.section_detect_threshold = 5000  # 5s para detectar nova seção
        self.learning_window = 10000  # 10s janela de aprendizado
        
    def load_cache(self):
        """Carrega cache de offsets adaptativos"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for track_key, track_data in data.items():
                        sections = []
                        for section_data in track_data.get('sections', []):
                            sections.append(SectionOffset(**section_data))
                        
                        self.cache[track_key] = AdaptiveOffsetData(
                            track_key=track_key,
                            base_offset=track_data.get('base_offset', 0),
                            sections=sections,
                            last_updated=track_data.get('last_updated', 0)
                        )
        except Exception as e:
            print(f"[OFFSET] Erro ao carregar cache adaptativo: {e}")
    
    def save_cache(self):
        """Salva cache de offsets adaptativos"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            data = {}
            for track_key, track_data in self.cache.items():
                sections_data = []
                for section in track_data.sections:
                    sections_data.append(asdict(section))
                
                data[track_key] = {
                    'track_key': track_data.track_key,
                    'base_offset': track_data.base_offset,
                    'sections': sections_data,
                    'last_updated': track_data.last_updated
                }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[OFFSET] Erro ao salvar cache adaptativo: {e}")
    
    def set_current_track(self, artist: str, title: str):
        """Define a faixa atual"""
        track_key = f"{artist.lower().strip()} - {title.lower().strip()}"
        
        if track_key not in self.cache:
            self.cache[track_key] = AdaptiveOffsetData(track_key)
        
        self.current_track = self.cache[track_key]
        self.current_section_index = -1
        print(f"[OFFSET] Faixa atual: {track_key}")
        print(f"[OFFSET] Seções existentes: {len(self.current_track.sections)}")
    
    def get_current_offset(self, progress_ms: int) -> int:
        """Retorna offset para o tempo atual, considerando seções"""
        if not self.current_track:
            return 0
        
        # Encontra seção ativa
        active_section = None
        for i, section in enumerate(self.current_track.sections):
            if section.start_time <= progress_ms < section.end_time:
                active_section = section
                self.current_section_index = i
                break
        
        if active_section:
            total_offset = self.current_track.base_offset + active_section.offset
            print(f"[OFFSET] Tempo: {progress_ms}ms | Seção {self.current_section_index} | Offset: {total_offset}ms")
            return total_offset
        
        # Se não está em nenhuma seção, usa offset base
        return self.current_track.base_offset
    
    def adjust_offset_at_position(self, progress_ms: int, delta: int):
        """Ajusta offset para uma posição específica da música"""
        if not self.current_track:
            return
        
        print(f"[OFFSET] Ajustando offset em {progress_ms}ms por {delta}ms")
        
        # Encontra ou cria seção para esta posição
        section = self._find_or_create_section(progress_ms)
        section.offset += delta
        section.user_adjusted = True
        section.confidence = 1.0
        
        self.current_track.last_updated = time.time()
        self.save_cache()
        
        print(f"[OFFSET] Seção {section.start_time}-{section.end_time}: offset={section.offset}ms")
    
    def _find_or_create_section(self, progress_ms: int) -> SectionOffset:
        """Encontra seção existente ou cria nova para a posição"""
        # Procura seção existente
        for section in self.current_track.sections:
            if section.start_time <= progress_ms < section.end_time:
                return section
        
        # Cria nova seção
        section_start = max(0, progress_ms - self.learning_window // 2)
        section_end = progress_ms + self.learning_window // 2
        
        # Ajusta limites para não sobrepor seções existentes
        for existing in self.current_track.sections:
            if existing.end_time > section_start and existing.start_time < section_end:
                # Ajusta para não sobrepor
                if existing.start_time > progress_ms:
                    section_end = min(section_end, existing.start_time)
                else:
                    section_start = max(section_start, existing.end_time)
        
        new_section = SectionOffset(
            start_time=section_start,
            end_time=section_end,
            offset=0,
            confidence=0.5,
            user_adjusted=False
        )
        
        # Insere na posição correta (ordenado por tempo)
        insert_pos = 0
        for i, section in enumerate(self.current_track.sections):
            if section.start_time > new_section.start_time:
                insert_pos = i
                break
            insert_pos = i + 1
        
        self.current_track.sections.insert(insert_pos, new_section)
        print(f"[OFFSET] Nova seção criada: {section_start}-{section_end}ms")
        
        return new_section
    
    def reset_all_offsets(self):
        """Reseta todos os offsets da faixa atual"""
        if not self.current_track:
            return
        
        self.current_track.base_offset = 0
        self.current_track.sections.clear()
        self.current_track.last_updated = time.time()
        self.save_cache()
        
        print(f"[OFFSET] Todos os offsets resetados para a faixa atual")
    
    def get_debug_info(self) -> str:
        """Retorna informações de debug sobre offsets"""
        if not self.current_track:
            return "Nenhuma faixa ativa"
        
        info = f"Faixa: {self.current_track.track_key}\n"
        info += f"Offset base: {self.current_track.base_offset}ms\n"
        info += f"Seções: {len(self.current_track.sections)}\n"
        
        for i, section in enumerate(self.current_track.sections):
            active = " [ATIVA]" if i == self.current_section_index else ""
            info += f"  {i}: {section.start_time//1000}-{section.end_time//1000}s = {section.offset}ms{active}\n"
        
        return info

# ===== RENDERIZADOR ANTI-SOBREPOSIÇÃO =====

class AntiOverlapRenderer:
    """Renderizador que previne sobreposição de texto"""
    
    def __init__(self, widget_width: int, widget_height: int):
        self.widget_width = widget_width
        self.widget_height = widget_height
        self.padding = 20
        self.min_line_spacing = 8
        self.max_visible_lines = 5
    
    def calculate_layout(self, lyrics: List[Tuple[int, int, str]], 
                        current_index: int) -> List[Dict]:
        """Calcula layout sem sobreposição"""
        if not lyrics or current_index < 0:
            return []
        
        # Define range de linhas visíveis
        start_idx = max(0, current_index - 2)
        end_idx = min(len(lyrics), current_index + 3)
        
        # Limita a max_visible_lines
        if end_idx - start_idx > self.max_visible_lines:
            end_idx = start_idx + self.max_visible_lines
        
        visible_lyrics = lyrics[start_idx:end_idx]
        layout = []
        
        # Calcula altura de cada linha
        total_height_needed = 0
        for i, (_, _, text) in enumerate(visible_lyrics):
            actual_index = start_idx + i
            is_current = (actual_index == current_index)
            
            font_size = 24 if is_current else 16
            font = QFont('Arial', font_size, QFont.Weight.Bold if is_current else QFont.Weight.Normal)
            metrics = QFontMetrics(font)
            
            # Calcula altura do texto com quebra de linha
            text_width = self.widget_width - (2 * self.padding)
            text_rect = metrics.boundingRect(0, 0, text_width, 0, 
                                           Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, 
                                           text)
            
            line_height = max(text_rect.height() + 10, 30)  # Altura mínima de 30px
            
            layout.append({
                'text': text,
                'font': font,
                'is_current': is_current,
                'height': line_height,
                'index': actual_index
            })
            
            total_height_needed += line_height + self.min_line_spacing
        
        # Remove último spacing
        if layout:
            total_height_needed -= self.min_line_spacing
        
        # Centraliza verticalmente se couber, senão prioriza linha atual
        available_height = self.widget_height - (2 * self.padding)
        
        if total_height_needed <= available_height:
            # Centraliza tudo
            start_y = self.padding + (available_height - total_height_needed) // 2
        else:
            # Prioriza linha atual no centro
            current_line_pos = next((i for i, item in enumerate(layout) if item['is_current']), 0)
            
            # Altura até a linha atual
            height_before_current = sum(
                layout[i]['height'] + self.min_line_spacing 
                for i in range(current_line_pos)
            )
            
            # Posição Y da linha atual no centro
            current_line_center = self.widget_height // 2
            start_y = current_line_center - height_before_current - layout[current_line_pos]['height'] // 2
            
            # Garante que não saia dos limites
            start_y = max(self.padding, min(start_y, 
                                          self.widget_height - total_height_needed - self.padding))
        
        # Atribui posições Y
        current_y = start_y
        for item in layout:
            item['y'] = current_y
            current_y += item['height'] + self.min_line_spacing
        
        return layout
    
    def render(self, painter: QPainter, layout: List[Dict]):
        """Renderiza o layout calculado"""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        for item in layout:
            # Configura fonte e cor
            painter.setFont(item['font'])
            
            if item['is_current']:
                painter.setPen(QPen(QColor(255, 255, 255, 255)))  # Branco total
            else:
                painter.setPen(QPen(QColor(255, 255, 255, 160)))  # Translúcido
            
            # Área de desenho
            text_rect = painter.fontMetrics().boundingRect(
                self.padding, item['y'], 
                self.widget_width - (2 * self.padding), item['height'],
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                item['text']
            )
            
            # Desenha o texto
            painter.drawText(
                self.padding, item['y'],
                self.widget_width - (2 * self.padding), item['height'],
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                item['text']
            )

# ===== JANELA CORRIGIDA =====

class FixedLyricsWindow(QWidget):
    """Janela com as correções aplicadas"""
    
    def __init__(self, sp, cache_dir: str = './cache'):
        super().__init__()
        
        # Gerenciadores
        self.offset_manager = AdaptiveOffsetManager(cache_dir)
        self.renderer = AntiOverlapRenderer(500, 200)  # Será atualizado no resize
        
        # Estado
        self.sp = sp
        self.current_lyrics: List[Tuple[int, int, str]] = []
        self.current_line_index = -1
        self.current_progress = 0
        self.current_track_id = None
        
        # Interface
        self.setWindowTitle('LetrasPIP - Corrigido')
        self.setGeometry(100, 100, 500, 200)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_display)
        self.timer.start(300)
        
        # Drag support
        self._drag_pos = None
        
        self.show()
        print("[FIXED] Janela corrigida inicializada")
    
    def update_display(self):
        """Atualização principal"""
        try:
            playback = self.sp.current_playback()
            if not playback or not playback.get('item'):
                return
            
            track_id = playback['item']['id']
            title = playback['item']['name']
            artist = ', '.join(a['name'] for a in playback['item']['artists'])
            progress = playback.get('progress_ms', 0)
            is_playing = playback.get('is_playing', False)
            
            # Mudança de faixa
            if track_id != self.current_track_id:
                print(f"[FIXED] Nova faixa: {artist} - {title}")
                self.current_track_id = track_id
                self.offset_manager.set_current_track(artist, title)
                # Aqui você integraria com seu sistema de busca de letras
                # self.current_lyrics = self.fetch_lyrics(title, artist)
            
            if is_playing:
                self.current_progress = progress
                self.update_sync()
            
            self.update()
            
        except Exception as e:
            print(f"[FIXED] Erro na atualização: {e}")
    
    def update_sync(self):
        """Atualiza sincronização com offset adaptativo"""
        if not self.current_lyrics:
            return
        
        # Aplica offset adaptativo
        progress_with_offset = self.current_progress + self.offset_manager.get_current_offset(self.current_progress)
        
        # Encontra linha atual
        new_index = -1
        for i, (start, end, text) in enumerate(self.current_lyrics):
            if start <= progress_with_offset < end:
                new_index = i
                break
        
        if new_index == -1:
            # Pega última linha válida
            for i in reversed(range(len(self.current_lyrics))):
                if self.current_lyrics[i][0] <= progress_with_offset:
                    new_index = i
                    break
        
        if new_index != self.current_line_index:
            self.current_line_index = new_index
    
    def paintEvent(self, event):
        """Renderização sem sobreposição"""
        painter = QPainter(self)
        
        # Fundo transparente (mantendo o existente)
        painter.setBrush(QBrush(QColor(0, 0, 0, 120)))
        painter.setPen(QPen(QColor(0, 0, 0, 0)))
        painter.drawRect(self.rect())
        
        # Atualiza renderer com dimensões atuais
        self.renderer.widget_width = self.width()
        self.renderer.widget_height = self.height()
        
        if not self.current_lyrics:
            # Mensagem de status
            painter.setFont(QFont('Arial', 16))
            painter.setPen(QPen(QColor(255, 255, 255, 200)))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Aguardando letras...")
        else:
            # Renderiza letras sem sobreposição
            layout = self.renderer.calculate_layout(self.current_lyrics, self.current_line_index)
            self.renderer.render(painter, layout)
        
        # Info do offset (canto inferior direito)
        current_offset = self.offset_manager.get_current_offset(self.current_progress)
        offset_text = f"Offset: {current_offset/1000:.2f}s"
        painter.setFont(QFont('Arial', 10))
        painter.setPen(QPen(QColor(200, 200, 200, 150)))
        painter.drawText(self.rect().adjusted(0, 0, -10, -5), 
                        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, 
                        offset_text)
    
    def keyPressEvent(self, event):
        """Controles de teclado"""
        if event.key() == Qt.Key.Key_Left:
            # Diminui offset na posição atual
            self.offset_manager.adjust_offset_at_position(self.current_progress, -500)
            print(f"[USER] Offset diminuído na posição {self.current_progress}ms")
            
        elif event.key() == Qt.Key.Key_Right:
            # Aumenta offset na posição atual
            self.offset_manager.adjust_offset_at_position(self.current_progress, 500)
            print(f"[USER] Offset aumentado na posição {self.current_progress}ms")
            
        elif event.key() == Qt.Key.Key_R:
            # Reset todos os offsets
            self.offset_manager.reset_all_offsets()
            print(f"[USER] Todos os offsets resetados")
            
        elif event.key() == Qt.Key.Key_D:
            # Debug info
            print(f"[DEBUG] {self.offset_manager.get_debug_info()}")
        
        self.update()
        event.accept()
    
    def mousePressEvent(self, event):
        """Suporte para arrastar"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Movimento de arrastar"""
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
    
    def resizeEvent(self, event):
        """Atualiza renderer quando redimensiona"""
        super().resizeEvent(event)
        self.renderer.widget_width = self.width()
        self.renderer.widget_height = self.height()

# ===== EXEMPLO DE USO =====

def main_fixed():
    """Exemplo de uso da versão corrigida"""
    import sys
    from PyQt6.QtWidgets import QApplication
    
    # Configure seu Spotify aqui
    # sp = spotipy.Spotify(auth_manager=SpotifyOAuth(...))
    
    app = QApplication(sys.argv)
    
    # Para teste, você pode passar None e simular dados
    window = FixedLyricsWindow(sp=None)  # Substitua por sua instância do Spotify
    
    # Dados de teste para "In the Aeroplane Over the Sea"
    test_lyrics = [
        (0, 10000, "What a beautiful face"),
        (10000, 20000, "I have found in this place"),
        (20000, 35000, "That is circling all round the sun"),
        (35000, 45000, "What a beautiful dream"),
        (45000, 55000, "That could flash on the screen"),
        (55000, 70000, "In a blink of an eye and be gone from me"),
        (70000, 85000, "Soft and sweet"),
        (85000, 95000, "Let me hold it close and keep it here with me"),
    ]
    
    window.current_lyrics = test_lyrics
    window.offset_manager.set_current_track("Neutral Milk Hotel", "In the Aeroplane Over the Sea")
    
    print("=== CONTROLES ===")
    print("← → : Ajustar offset na posição atual")
    print("R   : Resetar todos os offsets") 
    print("D   : Debug info")
    print("================")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main_fixed()