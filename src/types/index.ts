// Frontend TypeScript types matching Rust backend

export interface TrackInfo {
  id: string;
  name: string;
  artist: string;
  album: AlbumInfo;
  duration_ms: number;
  is_playing: boolean;
  progress_ms: number;
}

export interface AlbumInfo {
  name: string;
  images: ImageInfo[];
}

export interface ImageInfo {
  url: string;
  width?: number;
  height?: number;
}

export interface LyricsBlock {
  start: number;
  end: number;
  text: string;
}

export interface LyricsData {
  blocks: LyricsBlock[];
  quality: LyricsQuality;
  source?: string;
  confidence?: number;
  cached_at?: string;
}

export type LyricsQuality = 'Synced' | 'Unsynced' | 'Instrumental' | 'High' | 'Medium' | 'Low';

export interface SyncState {
  current_track?: TrackInfo;
  lyrics?: LyricsData;
  current_block_index: number;
  global_offset: number;
  is_paused: boolean;
  user_has_scrolled: boolean;
}

export interface AppSettings {
  fontSize: number;
  fontFamily: string;
  theme: 'dark' | 'light' | 'auto';
  window: {
    position?: [number, number];
    size?: [number, number];
    alwaysOnTop: boolean;
  };
  display: {
    showPreviousLine: boolean;
    showNextLine: boolean;
    animationDuration: number;
    scrollSnapDuration: number;
  };
}