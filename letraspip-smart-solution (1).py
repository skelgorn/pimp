# -*- coding: utf-8 -*-
"""
LetrasPIP - Solução Inteligente Integrada
Resolve: offset persistente, integração SRT/LRC, detecção inteligente, UX simplificado
"""

import re
import sys
import os
import json
import time
import threading
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt, QPoint, pyqtSlot, QTimer, QThread, pyqtSignal
from PyQt6.QtWidgets import QWidget, QApplication, QVBoxLayout, QLabel, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QAction, QIcon

import config

# Importar sistema de offset adaptativo
try:
    # Importação direta do código
    import importlib.util
    spec = importlib.util.spec_from_file_location("letraspip_fixes", "letraspip-fixes (1).py")
    letraspip_fixes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(letraspip_fixes)
    AdaptiveOffsetManager = letraspip_fixes.AdaptiveOffsetManager
    OFFSET_MANAGER_AVAILABLE = True
except Exception as e:
    OFFSET_MANAGER_AVAILABLE = False
    print(f"[WARNING] AdaptiveOffsetManager não disponível: {e}")

try:
    import lyricsgenius
    import syncedlyrics
    LIBS_AVAILABLE = True
except ImportError:
    LIBS_AVAILABLE = False

# ===== SISTEMA DE TIPOS E ESTADOS =====

class LyricsQuality(Enum):
    """Qualidade/tipo de letra encontrada"""
    SYNCED_HIGH = "synced_high"      # Sincronizada com boa qualidade
    SYNCED_LOW = "synced_low"        # Sincronizada com problemas
    PLAIN_TEXT = "plain_text"        # Apenas texto, sem sincronização
    INSTRUMENTAL = "instrumental"     # Música instrumental
    NOT_FOUND = "not_found"          # Não encontrou letra
    ERROR = "error"                   # Erro na busca
    SEARCHING = "searching"           # Estado de busca ativa

@dataclass
class LyricsData:
    """Container para dados de letra"""
    quality: LyricsQuality
    parsed_lyrics: List[Tuple[int, int, str]]  # [(start_ms, end_ms, text), ...]
    raw_text: str
    confidence: float  # 0.0 - 1.0
    source: str
    message: str  # Mensagem para o usuário

@dataclass
class OffsetState:
    """Estado do offset para uma faixa"""
    base_offset: int = 0        # Offset base da fonte de dados
    user_offset: int = 0        # Ajuste manual do usuário
    auto_offset: int = 0        # Ajuste automático (futuro ML)
    is_locked: bool = False     # Se o usuário "travou" o offset
    confidence: float = 1.0     # Confiança no offset atual
    
    @property
    def total_offset(self) -> int:
        return self.base_offset + self.user_offset + self.auto_offset

# ===== SISTEMA INTELIGENTE DE LETRAS =====

class SmartLyricsEngine:
    """Engine inteligente que integra múltiplas fontes e detecta qualidade"""
    
    def __init__(self):
        self.genius = None
        self.cache = {}
        self._init_apis()
    
    def _init_apis(self):
        """Inicializa APIs disponíveis"""
        if LIBS_AVAILABLE:
            try:
                # Configurar Genius se disponível
                if hasattr(config, 'GENIUS_ACCESS_TOKEN') and config.GENIUS_ACCESS_TOKEN:
                    self.genius = lyricsgenius.Genius(config.GENIUS_ACCESS_TOKEN, timeout=10)
            except Exception:
                pass
    
    def fetch_lyrics(self, track_name: str, artist_name: str) -> LyricsData:
        """Busca inteligente de letras com múltiplas fontes e heurística de instrumental/incompleta"""
        cache_key = f"{artist_name.lower()} - {track_name.lower()}"
        
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            return cached_result
        
        print(f"[LYRICS] Buscando: {cache_key}")

        # 1. Tentar letra sincronizada primeiro
        synced_data = self._try_synced_lyrics(track_name, artist_name)
        if synced_data.quality in [LyricsQuality.SYNCED_HIGH, LyricsQuality.SYNCED_LOW]:
            parsed = self._ensure_early_entry(synced_data.parsed_lyrics)
            synced_data = LyricsData(
                synced_data.quality, parsed, synced_data.raw_text,
                synced_data.confidence, synced_data.source, synced_data.message
            )
            self.cache[cache_key] = synced_data
            return synced_data
        else:
            print(f"[LYRICS] Syncedlyrics falhou: {synced_data.quality.value}")
        
        # 2. Tentar letra de texto simples
        plain_data = self._try_plain_lyrics(track_name, artist_name)
        if plain_data.quality == LyricsQuality.PLAIN_TEXT:
            print(f"[LYRICS] Genius sucesso: {len(plain_data.raw_text)} chars")
            # VERIFICAÇÃO ADICIONAL: se letra é muito pequena ou repetitiva
            if self._is_likely_instrumental_by_content(plain_data.raw_text):
                result = LyricsData(LyricsQuality.INSTRUMENTAL, [], "", 0.8, "content_analysis", "Música instrumental (conteúdo suspeito)")
                self.cache[cache_key] = result
                return result
            self.cache[cache_key] = plain_data
            return plain_data

        # 3. Detectar se é instrumental APENAS por palavras-chave óbvias
        if self._is_obviously_instrumental(track_name):
            print(f"[LYRICS] Instrumental detectado por nome: {track_name}")
            result = LyricsData(LyricsQuality.INSTRUMENTAL, [], "", 1.0, "detection", "Música instrumental detectada por nome")
            self.cache[cache_key] = result
            return result
        
        # 4. Se chegou aqui, realmente não encontrou letra
        print(f"[LYRICS] Nenhuma letra encontrada após busca completa")
        result = LyricsData(LyricsQuality.NOT_FOUND, [], "", 0.0, "comprehensive", "Letra não encontrada após busca completa")
        self.cache[cache_key] = result
        return result
    
    def _try_synced_lyrics(self, track_name: str, artist_name: str) -> LyricsData:
        """Tenta buscar letra sincronizada"""
        if not LIBS_AVAILABLE:
            return LyricsData(LyricsQuality.ERROR, [], "", 0.0, "syncedlyrics", 
                            "Biblioteca não disponível")
        
        try:
            query = f"{track_name} {artist_name}"
            synced_result = syncedlyrics.search(query)
            
            if synced_result and str(synced_result).strip():
                parsed = self._parse_synced_lyrics(synced_result)
                if parsed and len(parsed) > 0:
                    quality = self._analyze_sync_quality(parsed)
                    confidence = 0.9 if quality == LyricsQuality.SYNCED_HIGH else 0.6
                    message = "Letra sincronizada encontrada" if quality == LyricsQuality.SYNCED_HIGH else "Letra sincronizada com possíveis problemas"
                    
                    return LyricsData(quality, parsed, "", confidence, "syncedlyrics", message)
                else:
                    print(f"[LYRICS] Syncedlyrics: falha no parsing")
            else:
                print(f"[LYRICS] Syncedlyrics: resultado vazio ou None")
        
        except (Exception, TimeoutError) as e:
            print(f"[WARNING] Erro/timeout na busca sincronizada: {e}")
        
        return LyricsData(LyricsQuality.NOT_FOUND, [], "", 0.0, "syncedlyrics", "")
    
    def _try_plain_lyrics(self, track_name: str, artist_name: str) -> LyricsData:
        """Tenta buscar letra de texto simples"""
        if not self.genius:
            return LyricsData(LyricsQuality.ERROR, [], "", 0.0, "genius", 
                            "API Genius não configurada")
        
        try:
            result = self.genius.search_song(track_name, artist_name)
            if result and result.lyrics:
                clean_text = self._clean_lyrics_text(result.lyrics)
                if len(clean_text.strip()) > 0:  # Texto substantivo
                    parsed = [(0, 999999999, clean_text)]
                    return LyricsData(LyricsQuality.PLAIN_TEXT, parsed, clean_text, 
                                    0.7, "genius", "Letra encontrada (não sincronizada)")
        
        except Exception as e:
            print(f"Erro na busca Genius: {e}")
        
        return LyricsData(LyricsQuality.NOT_FOUND, [], "", 0.0, "genius", "")
    
    def _is_obviously_instrumental(self, track_name: str) -> bool:
        """Detecta se é instrumental APENAS por palavras-chave óbvias"""
        # Palavras-chave que indicam instrumental
        instrumental_keywords = [
            "instrumental", "interlude", "outro", "intro", "reprise", 
            "theme", "overture", "suite", "movement", "concerto"
        ]
        
        track_lower = track_name.lower()
        return any(keyword in track_lower for keyword in instrumental_keywords)
    
    def _parse_synced_lyrics(self, synced_result) -> List[Tuple[int, int, str]]:
        """Parser unificado para diferentes formatos de letra sincronizada"""
        if isinstance(synced_result, str) and '[' in synced_result:
            return self._parse_lrc_format(synced_result)
        elif isinstance(synced_result, list):
            return self._parse_list_format(synced_result)
        return []
    
    def _parse_lrc_format(self, lrc_content: str) -> List[Tuple[int, int, str]]:
        """Parse formato LRC"""
        lrc_line_regex = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\]\s*(.*)')
        times, texts = [], []
        
        for line in lrc_content.splitlines():
            match = lrc_line_regex.match(line)
            if match:
                minutes, seconds, hundredths, text = match.groups()
                if len(hundredths) == 2:
                    hundredths = f"{hundredths}0"
                
                time_ms = int(minutes) * 60000 + int(seconds) * 1000 + int(hundredths)
                clean_text = text.strip()
                
                if clean_text:  # Só adiciona se tiver texto
                    times.append(time_ms)
                    texts.append(clean_text)
        
        return self._build_time_blocks(times, texts)
    
    def _parse_list_format(self, list_data: list) -> List[Tuple[int, int, str]]:
        """Parse formato de lista"""
        times, texts = [], []
        
        for item in list_data:
            if isinstance(item, dict) and 'time' in item:
                time_ms = int(item['time'])
                text = item.get('text', '').strip()
                
                if text:
                    times.append(time_ms)
                    texts.append(text)
        
        return self._build_time_blocks(times, texts)
    
    def _build_time_blocks(self, times: List[int], texts: List[str]) -> List[Tuple[int, int, str]]:
        """Constrói blocos temporais com detecção de instrumentais e evita duplicidade antes de instrumentais"""
        if not times or not texts:
            return []
        blocks = []
        for i, (start, text) in enumerate(zip(times, texts)):
            end = times[i + 1] if i + 1 < len(times) else start + 10000
            blocks.append((start, end, text))
            # Detecta gap instrumental (> 8 segundos)
            if i + 1 < len(times):
                gap = times[i + 1] - end
                if gap > 8000:  # 8 segundos
                    # Só adiciona bloco instrumental se o texto anterior não for igual ao próximo
                    next_text = texts[i + 1] if (i + 1) < len(texts) else None
                    if text != next_text:
                        blocks.append((end, times[i + 1], "[Instrumental]"))
        # Remove duplicidades: se um bloco vocal termina e o próximo bloco (após instrumental) repete o mesmo texto, elimina o repetido
        deduped = []
        last_vocal = None
        for j, (start, end, text) in enumerate(blocks):
            # Remove duplicidade entre blocos vocais consecutivos
            if j > 0 and text == blocks[j-1][2] and text != "[Instrumental]":
                continue
            # Remove duplicidade vocal antes/depois de instrumental
            if text != "[Instrumental]":
                if last_vocal == text:
                    continue
                last_vocal = text
            else:
                last_vocal = None
            deduped.append((start, end, text))
        # Interpola blocos muito longos
        return self._interpolate_long_blocks(deduped)
    
    def _interpolate_long_blocks(self, blocks: List[Tuple[int, int, str]], 
                                max_duration: int = 6000) -> List[Tuple[int, int, str]]:
        """Interpola blocos longos para melhor controle de offset"""
        interpolated = []
        
        for start, end, text in blocks:
            duration = end - start
            
            if duration > max_duration and not text.startswith("["):
                # Divide em sub-blocos de max_duration
                current_time = start
                while current_time + max_duration < end:
                    interpolated.append((current_time, current_time + max_duration, text))
                    current_time += max_duration
                
                # Último fragmento
                if current_time < end:
                    interpolated.append((current_time, end, text))
            else:
                interpolated.append((start, end, text))
        
        return interpolated
    
    def _analyze_sync_quality(self, parsed_lyrics: List[Tuple[int, int, str]]) -> LyricsQuality:
        """Analisa qualidade da sincronização"""
        if not parsed_lyrics:
            return LyricsQuality.NOT_FOUND
        
        # Critérios de qualidade
        total_blocks = len(parsed_lyrics)
        long_blocks = sum(1 for start, end, text in parsed_lyrics if end - start > 10000)
        very_short_blocks = sum(1 for start, end, text in parsed_lyrics if end - start < 1000)
        
        # Proporção de problemas
        problem_ratio = (long_blocks + very_short_blocks) / total_blocks
        
        if problem_ratio < 0.2:  # Menos de 20% de problemas
            return LyricsQuality.SYNCED_HIGH
        else:
            return LyricsQuality.SYNCED_LOW
    
    def _clean_lyrics_text(self, lyrics: str) -> str:
        """Limpa texto de letra"""
        lines = lyrics.splitlines()
        cleaned = []
        
        for line in lines:
            # Remove metadados do Genius
            if any(word in line.lower() for word in ["contributor", "lyrics", "embed", "verse", "chorus"]):
                continue
            cleaned.append(line)
        
        return "\n".join(cleaned).strip()

    def _is_likely_instrumental_by_content(self, lyrics_text: str) -> bool:
        """Analisa conteúdo da letra para detectar instrumental (curta, repetitiva, vocalizações)"""
        if not lyrics_text or len(lyrics_text.strip()) < 5:
            return True
        
        clean_text = lyrics_text.lower().strip()
        
        # Detecta mensagens explícitas de instrumental do Genius
        instrumental_messages = [
            "this song is an instrumental",
            "this track is an instrumental", 
            "instrumental track",
            "no lyrics available",
            "purely instrumental",
            "instrumental version",
            "instrumental piece"
        ]
        
        for message in instrumental_messages:
            if message in clean_text:
                return True
        
        # Padrões originais de detecção
        instrumental_patterns = [
            r'^[a-z\s]{1,20}$',  # muito pouco texto
            r'^(la\s+){3,}', r'^(da\s+){3,}', r'^(dee\s+){2,}', r'^(doo\s+){2,}',
            r'^(oh\s+){3,}', r'^(ah\s+){3,}', r'^(na\s+){3,}', r'^(hey\s+){3,}'
        ]
        non_words = ['la', 'da', 'dee', 'doo', 'oh', 'ah', 'na', 'hey', 'mm', 'hmm', 'yeah', 'yo']
        words = clean_text.split()
        if len(words) > 0:
            non_word_ratio = sum(1 for word in words if word.strip() in non_words) / len(words)
            # Reforço: letra muito curta + muitas vocalizações
            # Ex.: "dee doo dee doo" → poucas palavras totais e >=70% de vocalizações
            if (len(words) < 15 and non_word_ratio >= 0.7) or non_word_ratio > 0.8:
                return True
        for pattern in instrumental_patterns:
            if re.search(pattern, clean_text):
                return True
        if len(clean_text) < 50:
            words_unique = set(words)
            if len(words) > 6 and len(words_unique) <= 3:
                return True
        return False
    
    def _ensure_early_entry(self, parsed_lyrics: List[Tuple[int, int, str]]) -> List[Tuple[int, int, str]]:
        """Remove placeholder artificial: nunca exibe 'Aguardando início vocal'."""
        if not parsed_lyrics:
            return parsed_lyrics
        # Não insere mais nenhum aviso, apenas retorna as lyrics reais
        return parsed_lyrics

# ===== GERENCIADOR DE OFFSET INTELIGENTE =====

class SmartOffsetManager:
    """Gerencia offsets de forma inteligente e persistente, agora por seção/bloco."""
    
    def __init__(self, cache_dir: str):
        self.cache_file = os.path.join(cache_dir, "smart_offset_cache.json")
        self.cache: Dict[str, OffsetState] = {}
        self.section_offsets: Dict[str, Dict[int, int]] = {}  # NOVO: faixa -> {indice_bloco: offset}
        self.current_track_key: Optional[str] = None
        self.load_cache()
    
    def load_cache(self):
        """Carrega cache de offsets"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, value in data.get('track_offsets', {}).items():
                        self.cache[key] = OffsetState(**value)
                    self.section_offsets = data.get('section_offsets', {})
        except Exception as e:
            print(f"Erro ao carregar cache de offsets: {e}")
    
    def save_cache(self):
        """Salva cache de offsets"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            data = {
                'track_offsets': {},
                'section_offsets': self.section_offsets
            }
            for key, state in self.cache.items():
                data['track_offsets'][key] = {
                    'base_offset': state.base_offset,
                    'user_offset': state.user_offset,
                    'auto_offset': state.auto_offset,
                    'is_locked': state.is_locked,
                    'confidence': state.confidence
                }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar cache de offsets: {e}")
    
    def get_track_key(self, artist: str, title: str) -> str:
        """Gera chave única para a faixa"""
        return f"{artist.lower().strip()} - {title.lower().strip()}"
    
    def set_current_track(self, artist: str, title: str):
        """Define a faixa atual"""
        self.current_track_key = self.get_track_key(artist, title)
        
        # Cria entrada se não existir
        if self.current_track_key not in self.cache:
            self.cache[self.current_track_key] = OffsetState()
        
        if self.current_track_key not in self.section_offsets:
            self.section_offsets[self.current_track_key] = {}
    
    def get_current_offset(self, progress: int = None, index: int = None) -> int:
        """Retorna offset total da faixa atual + offset do bloco (se index fornecido)"""
        if not self.current_track_key or self.current_track_key not in self.cache:
            return 0
        base = self.cache[self.current_track_key].total_offset
        # Corrige: só soma offset de seção se index for int e existir na seção
        if index is not None and isinstance(index, int):
            sec = self.section_offsets.get(self.current_track_key, {}).get(str(index), 0)
            return base + sec
        return base
    
    def adjust_offset_at_index(self, index: int, delta: int):
        """Ajusta offset do bloco/verso atual"""
        if not self.current_track_key:
            return
        idx = str(index)
        if self.current_track_key not in self.section_offsets:
            self.section_offsets[self.current_track_key] = {}
        self.section_offsets[self.current_track_key][idx] = self.section_offsets[self.current_track_key].get(idx, 0) + delta
        self.save_cache()
        print(f"[OFFSET] Ajuste manual por seção: bloco {index} | delta {delta}ms | total {self.section_offsets[self.current_track_key][idx]}ms")
    
    def get_offset_at_index(self, index: int) -> int:
        if not self.current_track_key:
            return 0
        return self.section_offsets.get(self.current_track_key, {}).get(str(index), 0)
    
    def reset_all_offsets(self):
        if not self.current_track_key:
            return
        if self.current_track_key in self.section_offsets:
            self.section_offsets[self.current_track_key] = {}
        if self.current_track_key in self.cache:
            self.cache[self.current_track_key].user_offset = 0
            self.cache[self.current_track_key].auto_offset = 0
            self.cache[self.current_track_key].is_locked = False
        self.save_cache()
        print(f"[OFFSET] Todos os offsets resetados para a faixa: {self.current_track_key}")
    
    def get_debug_info(self):
        return {
            'track_key': self.current_track_key,
            'track_offset': self.cache.get(self.current_track_key).__dict__ if self.current_track_key in self.cache else None,
            'section_offsets': self.section_offsets.get(self.current_track_key, {})
        }

# ===== SISTEMA DE LOGS INTELIGENTE =====

class SmartLogger:
    """Sistema de logs com separação inteligente de categorias"""
    
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.logs = {
            'main': [],      # Logs principais
            'user': [],      # Interações do usuário
            'sync': [],      # Problemas de sincronização
            'api': []        # Problemas de API
        }
        
        os.makedirs(base_dir, exist_ok=True)
    
    def log(self, category: str, message: str, level: str = "INFO"):
        """Adiciona log a uma categoria específica"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = f"[{timestamp}] [{level}] {message}"
        
        if category in self.logs:
            self.logs[category].append(entry)
            # Manter apenas últimas 1000 entradas
            if len(self.logs[category]) > 1000:
                self.logs[category] = self.logs[category][-1000:]
        
        # Print apenas logs importantes
        if level in ['ERROR', 'WARNING'] or category == 'user':
            print(entry)
    
    def log_user(self, action: str, details: str = ""):
        """Log específico para ações do usuário"""
        self.log('user', f"{action}: {details}", "USER")
    
    def log_sync(self, message: str, level: str = "INFO"):
        """Log específico para problemas de sincronização"""
        self.log('sync', message, level)
    
    def log_api(self, message: str, level: str = "INFO"):
        """Log específico para problemas de API"""
        self.log('api', message, level)
    
    def save_logs(self, category: str = None):
        """Salva logs de uma categoria específica ou todas"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if category and category in self.logs:
            filename = os.path.join(self.base_dir, f"{category}_{timestamp}.log")
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(self.logs[category]))
                return filename
            except Exception as e:
                print(f"Erro ao salvar logs de {category}: {e}")
        else:
            # Salva todas as categorias
            for cat, entries in self.logs.items():
                if entries:
                    filename = os.path.join(self.base_dir, f"{cat}_{timestamp}.log")
                    try:
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write('\n'.join(entries))
                    except Exception as e:
                        print(f"Erro ao salvar logs de {cat}: {e}")
    
    def get_logs(self, category: str, last_n: int = 100) -> List[str]:
        """Retorna últimas N entradas de uma categoria"""
        if category in self.logs:
            return self.logs[category][-last_n:]
        return []

# ===== INTERFACE PRINCIPAL INTELIGENTE =====

class SmartLyricsWindow(QWidget):
    """Interface principal com todas as melhorias integradas"""
    
    def __init__(self):
        super().__init__()
        
        # Inicializar componentes
        cache_dir = getattr(config, 'CACHE_DIR', './cache')
        os.makedirs(cache_dir, exist_ok=True)
        
        self.logger = SmartLogger(cache_dir)
        self.lyrics_engine = SmartLyricsEngine()
        try:
            if OFFSET_MANAGER_AVAILABLE:
                self.offset_manager = AdaptiveOffsetManager(cache_dir)
            else:
                self.offset_manager = SmartOffsetManager(cache_dir)
        except Exception:
            self.offset_manager = SmartOffsetManager(cache_dir)
         
        # Estado da interface
        self.current_lyrics: Optional[LyricsData] = None
        self.current_line_index = -1
        self.current_progress = 0
        self.current_line_phase = 0.0
        self.is_playing = False
        self.drag_position = None
         
        # Visual
        self.text_color = QColor(255, 255, 255, 230)  # base; futuro: cor da capa
        self.prev_next_alpha = 120
        self.prev_next_scale = 0.85
        self.line_spacing = 36  # px entre linhas
        self.scroll_pixels = 18  # deslocamento vertical ao longo do verso
        
        # Estado da faixa atual
        self.current_track_id = None
        self.current_artist = ""
        self.current_title = ""
        
        # Rolagem manual
        self.manual_scroll_offset = 0
        self.manual_scroll_active = False
        self.manual_scroll_timer = QTimer()
        
        self.logger.log('main', "LetrasPIP Smart inicializado")
        
        self.init_ui()
        self.setup_spotify()
        self.setup_timer()
        self.setup_tray()
    
    def init_ui(self):
        """Inicializa interface"""
        self.setWindowTitle('LetrasPIP Smart')
        # Janela um pouco maior por padrão (mas o desenho agora é responsivo)
        self.setGeometry(100, 100, 800, 300)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Centralizar na tela
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.center() - self.rect().center())
        
        self.show()
    
    def setup_spotify(self):
        """Configura conexão com Spotify"""
        try:
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                scope="user-read-playback-state",
                client_id=getattr(config, 'SPOTIPY_CLIENT_ID', ''),
                client_secret=getattr(config, 'SPOTIPY_CLIENT_SECRET', ''),
                redirect_uri=getattr(config, 'SPOTIPY_REDIRECT_URI', ''),
                cache_path=getattr(config, 'CACHE_FILE', './cache/.spotify_cache')
            ))
            # Teste imediato da conexão
            test_playback = self.sp.current_playback()
            self.logger.log('main', "Spotify configurado com sucesso")
            self.logger.log('api', f"Teste de conexão: {'OK' if test_playback is not None else 'Sem reprodução ativa'}")
        except Exception as e:
            self.logger.log('api', f"Erro ao configurar Spotify: {e}", "ERROR")
            self.sp = None
    
    def setup_timer(self):
        """Configura timer de atualização"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_display)
        self.timer.start(500)  # 500ms
    
    def setup_tray(self):
        """Cria a bandeja do sistema com controles de offset avançados"""
        from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
        from PyQt6.QtGui import QIcon, QAction
        # Conecta o timer agora que o método existe
        self.manual_scroll_timer.timeout.connect(self._disable_manual_scroll)
        
        self.tray_icon = QSystemTrayIcon(QIcon("icon.ico"), self)
        self.tray_menu = QMenu()

        # Menu minimalista: só ajustes globais
        self.action_sync_plus = QAction("Adiantar (+0,5s)", self)
        self.action_sync_minus = QAction("Atrasar (-0,5s)", self)
        self.action_sync_reset = QAction("Desfazer ajuste", self)
        self.action_quit = QAction("Sair", self)

        self.tray_menu.addAction(self.action_sync_plus)
        self.tray_menu.addAction(self.action_sync_minus)
        self.tray_menu.addAction(self.action_sync_reset)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.action_quit)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()

        self.action_sync_plus.triggered.connect(lambda: self._tray_adjust_offset_global(+500))
        self.action_sync_minus.triggered.connect(lambda: self._tray_adjust_offset_global(-500))
        self.action_sync_reset.triggered.connect(self._tray_reset_offset_global)
        self.action_quit.triggered.connect(QApplication.instance().quit)

    def _tray_adjust_offset_global(self, delta):
        """
        Ajuste inteligente: se o usuário só ajustou globalmente até agora, aplica global.
        Se já existe ajuste local neste trecho, passa a ajustar só o trecho.
        Se o usuário alterna muito, sugere (via log) resetar para padronizar.
        """
        track_key = getattr(self.offset_manager, 'current_track_key', None)
        idx = str(self.current_line_index) if self.current_line_index is not None else None
        # Heurística: se só existe user_offset ou nenhum ajuste local, aplica global
        section_offsets = getattr(self.offset_manager, 'section_offsets', {})
        has_local = track_key in section_offsets and section_offsets[track_key]
        if not has_local:
            # Ajuste global
            if hasattr(self.offset_manager, 'cache') and track_key in self.offset_manager.cache:
                self.offset_manager.cache[track_key].user_offset += delta
                self.offset_manager.save_cache()
                self.logger.log_user('offset_adjust_global', f'{delta}ms (tray-smart)')
        else:
            # Ajuste local só para o bloco atual
            if hasattr(self.offset_manager, 'adjust_offset_at_index') and self.current_line_index is not None and self.current_line_index >= 0:
                self.offset_manager.adjust_offset_at_index(self.current_line_index, delta)
                self.logger.log_user('offset_adjust_local', f'{delta}ms (tray-smart) bloco {self.current_line_index}')
        self.update_sync()
        self.update()  # Redesenha interface
    
    def _tray_reset_offset_global(self):
        """Reset compatível com AdaptiveOffsetManager e SmartOffsetManager"""
        # Para AdaptiveOffsetManager
        if hasattr(self.offset_manager, 'reset_all_offsets'):
            self.offset_manager.reset_all_offsets()
            self.logger.log_user('offset_reset_global', 'tray-adaptive')
        # Para SmartOffsetManager
        elif hasattr(self.offset_manager, 'cache'):
            track_key = getattr(self.offset_manager, 'current_track_key', None)
            if track_key and track_key in self.offset_manager.cache:
                self.offset_manager.cache[track_key].user_offset = 0
                if hasattr(self.offset_manager, 'section_offsets') and track_key in self.offset_manager.section_offsets:
                    self.offset_manager.section_offsets[track_key] = {}
                self.offset_manager.save_cache()
                self.logger.log_user('offset_reset_global', 'tray-smart')
        # Fallback genérico
        elif hasattr(self.offset_manager, 'reset_user_offset'):
            self.offset_manager.reset_user_offset()
            self.logger.log_user('offset_reset_global', 'tray-fallback')
        else:
            self.logger.log_user('offset_reset_global', 'não suportado pelo offset_manager atual')
        
        self.update_sync()
        self.update()
    
    def get_spotify_status(self) -> Tuple[Optional[str], str, str, int, bool]:
        """Retorna status atual do Spotify"""
        if not self.sp:
            return None, "", "", 0, False
        
        try:
            playback = self.sp.current_playback()
            
            if not playback or not playback.get('item'):
                return None, "", "", 0, False
            
            track_id = playback['item']['id']
            title = playback['item']['name']
            artist = ', '.join(artist['name'] for artist in playback['item']['artists'])
            progress = playback.get('progress_ms', 0)
            is_playing = playback.get('is_playing', False)
            
            return track_id, title, artist, progress, is_playing
            
        except Exception as e:
            print(f"[ERROR] Erro ao buscar status Spotify: {e}")
            self.logger.log('api', f"Erro ao buscar status Spotify: {e}", "WARNING")
            return None, "", "", 0, False

    def update_display(self):
        """Atualização principal - evita chamadas duplicadas"""
        if getattr(self, '_updating', False):
            return  # Evita recursão
        
        self._updating = True
        try:
            track_id, title, artist, progress, is_playing = self.get_spotify_status()
            
            if not is_playing:
                self.current_progress = 0
                self.current_line_index = -1
                self.is_playing = False
                self.update()
                return
            
            self.is_playing = True
            
            # Só atualiza se mudou significativamente
            if abs(progress - getattr(self, '_last_progress', 0)) < 100:
                return  # Skip update se mudança < 100ms
                
            self._last_progress = progress
            self.current_progress = progress
            
            # Busca letra se necessário
            if artist and title:
                track_key = f"{artist.lower()} - {title.lower()}"
                
                current_key = getattr(self, '_current_track_key', '')
                
                if track_key != current_key:
                    self._current_track_key = track_key
                    self.handle_track_change(track_id, title, artist)
                else:
                    self.update_sync()
                    self.update()
            
            else:
                self.current_lyrics = None
                self.update()
        
        finally:
            self._updating = False
    
    def handle_track_change(self, track_id: Optional[str], title: str, artist: str):
        """Lida com mudança de faixa - exibe letra do cache instantaneamente e busca nova em thread"""
        self.current_track_id = track_id
        self.current_title = title
        self.current_artist = artist

        if not track_id:
            self.current_lyrics = None
            self.update()
            return

        # Define faixa atual no gerenciador de offset
        self.offset_manager.set_current_track(artist, title)

        # Busca letra do cache (instantâneo)
        cache_key = f"{artist.lower()} - {title.lower()}"
        cached_lyrics = self.lyrics_engine.cache.get(cache_key)
        if cached_lyrics:
            self.current_lyrics = cached_lyrics
        else:
            self.current_lyrics = LyricsData(
                LyricsQuality.SEARCHING,
                [], "", 0.0, "cache",
                "Carregando..."
            )
        self.update()  # Atualiza interface imediatamente

        # Inicia busca real em thread
        import threading
        threading.Thread(
            target=self._async_fetch_lyrics,
            args=(title, artist, cache_key),
            daemon=True
        ).start()

    def _async_fetch_lyrics(self, title: str, artist: str, cache_key: str):
        """Busca letra de forma assíncrona e atualiza interface ao terminar"""
        lyrics = self.lyrics_engine.fetch_lyrics(title, artist)
        self.lyrics_engine.cache[cache_key] = lyrics
        self.current_lyrics = lyrics
        self.logger.log('main', f"Letra atualizada: {lyrics.quality}")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self.update)

    def update_sync(self):
        """Atualiza sincronização das letras"""
        if not self.current_lyrics or not self.current_lyrics.parsed_lyrics:
            return
        
        # Aplica offset total
        try:
            total_offset = self.offset_manager.get_current_offset(self.current_progress, self.current_line_index)
        except TypeError:
            total_offset = self.offset_manager.get_current_offset(self.current_progress)
        progress_with_offset = self.current_progress + total_offset
        
        # Encontra linha atual
        new_index = self.get_current_synced_index(progress_with_offset)
        
        # Atualiza se mudou
        if new_index != self.current_line_index:
            self.current_line_index = new_index
            self.logger.log('sync', f"Linha atual: {new_index}")
        
        # Salva progresso normalizado do verso atual para rolagem suave
        if 0 <= self.current_line_index < len(self.current_lyrics.parsed_lyrics):
            start, end, _ = self.current_lyrics.parsed_lyrics[self.current_line_index]
            dur = max(1, end - start)
            self.current_line_phase = max(0.0, min(1.0, (progress_with_offset - start) / dur))
        else:
            self.current_line_phase = 0.0
    
    def get_current_synced_index(self, current_time_ms: int) -> int:
        """Retorna o índice do verso sincronizado para o tempo atual.
        Se o tempo for antes do primeiro timestamp, retorna 0 para exibir o primeiro verso imediatamente."""
        parsed = self.current_lyrics.parsed_lyrics
        if not parsed:
            return -1
        for i, (start, end, _) in enumerate(parsed):
            if current_time_ms < start:
                return max(0, i - 1)
            if start <= current_time_ms < end:
                return i
        return len(parsed) - 1

    def update_current_line_index(self, current_time_ms: int):
        """Atualiza o índice da linha atual sincronizada, exibindo o primeiro verso desde o início da música."""
        self.current_line_index = self.get_current_synced_index(current_time_ms)

    def paintEvent(self, event):
        """Renderiza interface"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        # Limpa a área com transparência para evitar ghosting ao clicar
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        
        if not self.current_lyrics:
            # Mensagens inteligentes baseadas no estado
            if not self.current_track_id:
                self.draw_status_message(painter, "Aguardando música...")
            elif not self.is_playing:
                self.draw_status_message(painter, "Música pausada", QColor(200, 200, 255))
            else:
                self.draw_status_message(painter, "Buscando letras...", QColor(255, 200, 100))
            self.draw_offset_info(painter)
            return
        
        # Renderiza baseado na qualidade da letra
        if self.current_lyrics.quality in (LyricsQuality.SYNCED_HIGH, LyricsQuality.SYNCED_LOW):
            if not self.is_playing:
                self.draw_status_message(painter, "Música pausada\n(Letras sincronizadas disponíveis)", QColor(200, 200, 255))
            else:
                self.draw_synced_lyrics(painter, warning=(self.current_lyrics.quality == LyricsQuality.SYNCED_LOW))
        elif self.current_lyrics.quality == LyricsQuality.PLAIN_TEXT:
            if not self.is_playing:
                self.draw_status_message(painter, "Música pausada\n(Letras sem sincronização)", QColor(200, 200, 255))
            else:
                self.draw_plain_lyrics(painter)
        elif self.current_lyrics.quality == LyricsQuality.INSTRUMENTAL:
            self.draw_status_message(painter, "Música Instrumental", QColor(100, 150, 255))
        elif self.current_lyrics.quality == LyricsQuality.NOT_FOUND:
            self.draw_status_message(painter, "Letra não encontrada", QColor(255, 150, 100))
        elif self.current_lyrics.quality == LyricsQuality.SEARCHING:
            self.draw_status_message(painter, "Buscando letras...", QColor(255, 200, 100))
        else:
            self.draw_status_message(painter, "Erro na busca de letras", QColor(255, 100, 100))
        
        # Info do offset no canto
        self.draw_offset_info(painter)

    def draw_status_message(self, painter: QPainter, message: str, color: QColor = None):
        """Desenha mensagem de status centralizada"""
        if color is None:
            color = QColor(255, 255, 255, 200)
        
        painter.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        painter.setPen(QPen(color))
        
        rect = self.rect().adjusted(20, 20, -20, -20)
        flags = Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap
        painter.drawText(rect, int(flags), message)
    
    def draw_synced_lyrics(self, painter: QPainter, warning: bool = False):
        """Desenha letras sincronizadas com 3 slots (anterior distinto, central, próximo distinto),
        pulando repetições consecutivas do bloco central."""
        if self.current_line_index < 0 or self.current_line_index >= len(self.current_lyrics.parsed_lyrics):
            return
        spacing = max(36, int(self.height() * 0.18))
        center_y = self.rect().center().y()
        # Central
        central_text = self.current_lyrics.parsed_lyrics[self.current_line_index][2]
        # Busca anterior distinto
        prev_idx = self.current_line_index - 1
        while prev_idx >= 0 and self.current_lyrics.parsed_lyrics[prev_idx][2] == central_text:
            prev_idx -= 1
        # Busca próximo distinto
        next_idx = self.current_line_index + 1
        while next_idx < len(self.current_lyrics.parsed_lyrics) and self.current_lyrics.parsed_lyrics[next_idx][2] == central_text:
            next_idx += 1
        # Monta lista de índices para slots: [anterior, central, próximo]
        slot_indices = [prev_idx, self.current_line_index, next_idx]
        for rel_idx, idx in zip([-1, 0, 1], slot_indices):
            if 0 <= idx < len(self.current_lyrics.parsed_lyrics):
                text = self.current_lyrics.parsed_lyrics[idx][2]
            else:
                text = ""
            if rel_idx == 0:
                font = QFont('Arial', 22, QFont.Weight.Bold)
                color = QColor(self.text_color)
                if warning:
                    color = QColor(255, 200, 120, 230)
            else:
                font = QFont('Arial', int(22 * self.prev_next_scale))
                color = QColor(self.text_color)
                color.setAlpha(self.prev_next_alpha)

            painter.setFont(font)
            painter.setPen(QPen(color))
            metrics = painter.fontMetrics()
            text_height = metrics.height()

            # Calcular posição Y com melhor espaçamento
            y_pos = center_y + rel_idx * spacing
            
            # Criar retângulo com margens adequadas e altura suficiente
            margin = 40
            
            # Calcular altura real do texto com word wrap
            temp_rect = QtCore.QRect(margin, 0, self.width() - 2 * margin, 1000)  # Altura temporária grande
            actual_text_rect = metrics.boundingRect(temp_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)
            actual_height = actual_text_rect.height()
            
            # Usar altura real + padding
            rect_height = max(text_height + 16, actual_height + 20)  # Padding extra para multi-linha
            top = y_pos - rect_height // 2
            
            # Garantir que o retângulo não saia da janela com margem de segurança
            min_top = 10
            max_bottom = self.height() - 10
            
            if top < min_top:
                top = min_top
            if top + rect_height > max_bottom:
                top = max_bottom - rect_height
                # Se ainda não couber, reduzir altura
                if top < min_top:
                    top = min_top
                    rect_height = max_bottom - min_top
                
            rect = QtCore.QRect(margin, top, self.width() - 2 * margin, rect_height)
            
            # Usar TextWordWrap com AlignCenter para melhor quebra de linha
            flags = Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap
            
            # Desenhar com retângulo bem definido
            painter.drawText(rect, int(flags), text)
    
    def draw_plain_lyrics(self, painter: QPainter):
        """Desenha letras de texto simples centralizadas"""
        painter.setFont(QFont('Arial', 18))
        color = QColor(self.text_color)
        painter.setPen(QPen(color))
        rect = self.rect().adjusted(24, 24, -24, -24)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, 
                         self.current_lyrics.raw_text)
    
    def draw_offset_info(self, painter: QPainter):
        """Desenha info do offset no canto"""
        painter.setFont(QFont('Arial', 10))
        painter.setPen(QPen(QColor(255, 255, 255, 150)))
        
        try:
            # Verificar se get_current_offset aceita parâmetros
            import inspect
            if hasattr(self, 'offset_manager'):
                sig = inspect.signature(self.offset_manager.get_current_offset)
                if len(sig.parameters) > 1:  # tem parâmetros além de self
                    total_offset = self.offset_manager.get_current_offset(self.current_progress, self.current_line_index)
                else:
                    total_offset = self.offset_manager.get_current_offset(self.current_progress)
            else:
                total_offset = 0
        except Exception:
            total_offset = 0
        
        offset_text = f"Offset: {total_offset}ms"
        painter.drawText(10, 16, offset_text)

    def get_lyrics_status_message(self):
        """
        Retorna uma string curta com a fonte e tipo da letra atual.
        """
        if not self.current_lyrics:
            return "Buscando letra..."
        q = self.current_lyrics.quality
        src = (self.current_lyrics.source or "").capitalize()
        if q.name.startswith("SYNCED"):
            return f"Letra sincronizada ({src})"
        elif q == LyricsQuality.PLAIN_TEXT:
            return f"Letra simples ({src})"
        elif q == LyricsQuality.INSTRUMENTAL:
            return "Instrumental detectado"
        elif q == LyricsQuality.NOT_FOUND:
            return "Letra não encontrada"
        elif q == LyricsQuality.SEARCHING:
            return "Buscando letra..."
        else:
            return "Status desconhecido"

    def mousePressEvent(self, event):
        """Inicia arrastar janela"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Arrasta janela"""
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Finaliza arrastar"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = None
            event.accept()

    def _disable_manual_scroll(self):
        """Desabilita rolagem manual temporariamente"""
        if hasattr(self, 'manual_scroll_disabled'):
            self.manual_scroll_disabled = True
            self.logger.log_user(" Rolagem manual desabilitada temporariamente")
        else:
            # Fallback se atributo não existir
            self.manual_scroll_disabled = True
            print("[DEBUG] _disable_manual_scroll: Atributo criado e definido como True")

# ===== PONTO DE ENTRADA =====

def main():
    """Ponto de entrada principal"""
    print("[DEBUG] Iniciando LetrasPIP Smart...")
    
    app = QApplication(sys.argv)
    
    try:
        print("[DEBUG] Criando janela...")
        window = SmartLyricsWindow()
        window.show()
        
        print("[INFO] LetrasPIP Smart iniciado com sucesso!")
        print("[INFO] Controles:")
        print("  ← / → : Ajustar offset ±500ms")
        print("  R     : Reset offset")
        print("  D     : Debug offset")
        
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"[ERROR] Erro ao iniciar: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()