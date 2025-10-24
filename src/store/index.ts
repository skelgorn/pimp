// Zustand store for app state management

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import { SyncState, TrackInfo, LyricsData, AppSettings } from '../types';

interface AppStore {
  // Sync state
  syncState: SyncState;
  setSyncState: (state: Partial<SyncState>) => void;

  // Current track
  currentTrack: TrackInfo | null;
  setCurrentTrack: (track: TrackInfo | null) => void;

  // Lyrics
  lyrics: LyricsData | null;
  setLyrics: (lyrics: LyricsData | null) => void;

  // UI state
  isDebugVisible: boolean;
  setDebugVisible: (visible: boolean) => void;

  // Settings
  settings: AppSettings;
  updateSettings: (settings: Partial<AppSettings>) => void;

  // Progress tracking
  progress: number;
  setProgress: (progress: number) => void;

  // User interaction
  userHasScrolled: boolean;
  setUserHasScrolled: (scrolled: boolean) => void;

  // Connection state
  isConnected: boolean;
  setConnected: (connected: boolean) => void;

  // Error state
  error: string | null;
  setError: (error: string | null) => void;
}

const defaultSettings: AppSettings = {
  fontSize: 18,
  fontFamily: 'Segoe UI',
  theme: 'auto',
  window: {
    alwaysOnTop: true,
  },
  display: {
    showPreviousLine: true,
    showNextLine: true,
    animationDuration: 300,
    scrollSnapDuration: 3000,
  },
};

export const useAppStore = create<AppStore>()(
  subscribeWithSelector((set, _get) => ({
    // Initial state
    syncState: {
      current_block_index: -1,
      global_offset: 0,
      is_paused: false,
      user_has_scrolled: false,
    },
    setSyncState: (state) =>
      set((prev) => ({
        syncState: { ...prev.syncState, ...state },
      })),

    currentTrack: null,
    setCurrentTrack: (track) => set({ currentTrack: track }),

    lyrics: null,
    setLyrics: (lyrics) => set({ lyrics }),

    isDebugVisible: false,
    setDebugVisible: (visible) => set({ isDebugVisible: visible }),

    settings: defaultSettings,
    updateSettings: (newSettings) =>
      set((prev) => ({
        settings: { ...prev.settings, ...newSettings },
      })),

    progress: 0,
    setProgress: (progress) => set({ progress }),

    userHasScrolled: false,
    setUserHasScrolled: (scrolled) => set({ userHasScrolled: scrolled }),

    isConnected: false,
    setConnected: (connected) => set({ isConnected: connected }),

    error: null,
    setError: (error) => set({ error }),
  }))
);

// Selectors for optimized re-renders
export const selectCurrentTrack = (state: AppStore) => state.currentTrack;
export const selectLyrics = (state: AppStore) => state.lyrics;
export const selectSyncState = (state: AppStore) => state.syncState;
export const selectSettings = (state: AppStore) => state.settings;
export const selectProgress = (state: AppStore) => state.progress;
export const selectIsConnected = (state: AppStore) => state.isConnected;
export const selectError = (state: AppStore) => state.error;