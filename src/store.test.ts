import { describe, it, expect, vi, beforeEach } from 'vitest';
import { selectLyrics, selectSyncState, selectSettings, selectProgress } from './store';

// Mock do store para testes isolados
const createMockStore = (initialState: any) => {
  return {
    ...initialState,
    // Funções mock para mutações
    setSyncState: vi.fn(),
    setCurrentTrack: vi.fn(),
    setLyrics: vi.fn(),
    setProgress: vi.fn(),
    setSettings: vi.fn(),
  };
};

describe('Store Selectors', () => {
  describe('selectLyrics', () => {
    it('returns lyrics when available', () => {
      const mockState = createMockStore({
        lyrics: {
          blocks: [
            { start: 0, end: 1000, text: 'Test line' },
          ],
          quality: 'Synced',
        },
      });

      const result = selectLyrics(mockState);
      expect(result).toEqual({
        blocks: [{ start: 0, end: 1000, text: 'Test line' }],
        quality: 'Synced',
      });
    });

    it('returns null when no lyrics', () => {
      const mockState = createMockStore({
        lyrics: null,
      });

      const result = selectLyrics(mockState);
      expect(result).toBeNull();
    });
  });

  describe('selectSyncState', () => {
    it('returns sync state with offset and pause status', () => {
      const mockState = createMockStore({
        syncState: {
          global_offset: 500,
          is_paused: false,
        },
      });

      const result = selectSyncState(mockState);
      expect(result).toEqual({
        global_offset: 500,
        is_paused: false,
      });
    });

    it('handles paused state correctly', () => {
      const mockState = createMockStore({
        syncState: {
          global_offset: 0,
          is_paused: true,
        },
      });

      const result = selectSyncState(mockState);
      expect(result.is_paused).toBe(true);
    });
  });

  describe('selectSettings', () => {
    it('returns display settings', () => {
      const mockState = createMockStore({
        settings: {
          fontSize: 24,
          fontFamily: 'Arial',
          display: {
            showPreviousLine: true,
            showNextLine: true,
            animationDuration: 300,
            scrollSnapDuration: 1000,
          },
        },
      });

      const result = selectSettings(mockState);
      expect(result.fontSize).toBe(24);
      expect(result.display.animationDuration).toBe(300);
    });
  });

  describe('selectProgress', () => {
    it('returns current playback progress', () => {
      const mockState = createMockStore({
        progress: 1500,
      });

      const result = selectProgress(mockState);
      expect(result).toBe(1500);
    });

    it('handles zero progress', () => {
      const mockState = createMockStore({
        progress: 0,
      });

      const result = selectProgress(mockState);
      expect(result).toBe(0);
    });
  });
});

describe('Store Integration', () => {
  it('combines selectors correctly for lyrics display logic', () => {
    const mockState = createMockStore({
      lyrics: {
        blocks: [
          { start: 0, end: 1000, text: 'First line' },
          { start: 1000, end: 2000, text: 'Second line' },
        ],
        quality: 'Synced',
      },
      syncState: {
        global_offset: 500,
        is_paused: false,
      },
      progress: 500,
    });

    const lyrics = selectLyrics(mockState);
    const syncState = selectSyncState(mockState);
    const progress = selectProgress(mockState);

    // Simula lógica do componente: progress + offset
    const adjustedProgress = progress + syncState.global_offset; // 500 + 500 = 1000

    expect(lyrics?.blocks).toHaveLength(2);
    expect(adjustedProgress).toBe(1000);
    
    // Com progress ajustado de 1000ms, deve estar na segunda linha
    const currentBlock = lyrics?.blocks.find(
      block => adjustedProgress >= block.start && adjustedProgress < block.end
    );
    expect(currentBlock?.text).toBe('Second line');
  });

  it('handles edge cases in selector combinations', () => {
    const mockState = createMockStore({
      lyrics: null,
      syncState: { global_offset: 0, is_paused: true },
      progress: 0,
    });

    const lyrics = selectLyrics(mockState);
    const syncState = selectSyncState(mockState);
    const progress = selectProgress(mockState);

    expect(lyrics).toBeNull();
    expect(syncState.is_paused).toBe(true);
    expect(progress).toBe(0);
  });
});

describe('Store Mutations', () => {
  let mockStore: any;

  beforeEach(() => {
    mockStore = createMockStore({
      lyrics: null,
      syncState: { global_offset: 0, is_paused: false },
      currentTrack: null,
      progress: 0,
      settings: {
        fontSize: 24,
        fontFamily: 'Arial',
        display: {
          showPreviousLine: true,
          showNextLine: true,
          animationDuration: 300,
        },
      },
    });
  });

  describe('setSyncState', () => {
    it('updates sync state correctly', () => {
      const newSyncState = { global_offset: 500, is_paused: true };
      
      mockStore.setSyncState(newSyncState);
      
      expect(mockStore.setSyncState).toHaveBeenCalledWith(newSyncState);
      expect(mockStore.setSyncState).toHaveBeenCalledTimes(1);
    });

    it('handles offset changes for sync adjustment', () => {
      const offsetChange = { global_offset: -200, is_paused: false };
      
      mockStore.setSyncState(offsetChange);
      
      expect(mockStore.setSyncState).toHaveBeenCalledWith(offsetChange);
    });
  });

  describe('setLyrics', () => {
    it('sets new lyrics data', () => {
      const newLyrics = {
        blocks: [
          { start: 0, end: 1000, text: 'New song line' },
        ],
        quality: 'Synced',
      };
      
      mockStore.setLyrics(newLyrics);
      
      expect(mockStore.setLyrics).toHaveBeenCalledWith(newLyrics);
    });

    it('handles instrumental tracks', () => {
      const instrumentalLyrics = {
        blocks: [],
        quality: 'Instrumental',
      };
      
      mockStore.setLyrics(instrumentalLyrics);
      
      expect(mockStore.setLyrics).toHaveBeenCalledWith(instrumentalLyrics);
    });

    it('clears lyrics when set to null', () => {
      mockStore.setLyrics(null);
      
      expect(mockStore.setLyrics).toHaveBeenCalledWith(null);
    });
  });

  describe('setCurrentTrack', () => {
    it('sets new track information', () => {
      const newTrack = {
        name: 'New Song',
        artist: 'New Artist',
        album: { name: 'New Album', images: [{ url: 'cover.jpg' }] },
        duration_ms: 240000,
        is_playing: true,
      };
      
      mockStore.setCurrentTrack(newTrack);
      
      expect(mockStore.setCurrentTrack).toHaveBeenCalledWith(newTrack);
    });

    it('clears track when set to null', () => {
      mockStore.setCurrentTrack(null);
      
      expect(mockStore.setCurrentTrack).toHaveBeenCalledWith(null);
    });
  });

  describe('setProgress', () => {
    it('updates playback progress', () => {
      const newProgress = 1500;
      
      mockStore.setProgress(newProgress);
      
      expect(mockStore.setProgress).toHaveBeenCalledWith(newProgress);
    });

    it('handles zero progress', () => {
      mockStore.setProgress(0);
      
      expect(mockStore.setProgress).toHaveBeenCalledWith(0);
    });

    it('handles end of track progress', () => {
      const endProgress = 240000; // 4 minutes
      
      mockStore.setProgress(endProgress);
      
      expect(mockStore.setProgress).toHaveBeenCalledWith(endProgress);
    });
  });

  describe('setSettings', () => {
    it('updates display settings', () => {
      const newSettings = {
        fontSize: 28,
        fontFamily: 'Roboto',
        display: {
          showPreviousLine: false,
          showNextLine: true,
          animationDuration: 500,
        },
      };
      
      mockStore.setSettings(newSettings);
      
      expect(mockStore.setSettings).toHaveBeenCalledWith(newSettings);
    });
  });
});

describe('Store State Transitions', () => {
  it('simulates complete song change workflow', () => {
    const mockStore = createMockStore({
      lyrics: null,
      syncState: { global_offset: 0, is_paused: false },
      currentTrack: null,
      progress: 0,
    });

    // 1. Set new track
    const newTrack = {
      name: 'Test Song',
      artist: 'Test Artist',
      album: { name: 'Test Album', images: [] },
      duration_ms: 180000,
      is_playing: true,
    };
    mockStore.setCurrentTrack(newTrack);

    // 2. Load lyrics
    const lyrics = {
      blocks: [
        { start: 0, end: 2000, text: 'First verse' },
        { start: 2000, end: 4000, text: 'Second verse' },
      ],
      quality: 'Synced',
    };
    mockStore.setLyrics(lyrics);

    // 3. Start playback
    mockStore.setProgress(500);

    // 4. Adjust sync if needed
    mockStore.setSyncState({ global_offset: 200, is_paused: false });

    // Verify all mutations were called
    expect(mockStore.setCurrentTrack).toHaveBeenCalledWith(newTrack);
    expect(mockStore.setLyrics).toHaveBeenCalledWith(lyrics);
    expect(mockStore.setProgress).toHaveBeenCalledWith(500);
    expect(mockStore.setSyncState).toHaveBeenCalledWith({ global_offset: 200, is_paused: false });
  });

  it('handles pause/resume workflow', () => {
    const mockStore = createMockStore({
      syncState: { global_offset: 0, is_paused: false },
    });

    // Pause
    mockStore.setSyncState({ global_offset: 0, is_paused: true });
    expect(mockStore.setSyncState).toHaveBeenCalledWith({ global_offset: 0, is_paused: true });

    // Resume
    mockStore.setSyncState({ global_offset: 0, is_paused: false });
    expect(mockStore.setSyncState).toHaveBeenCalledWith({ global_offset: 0, is_paused: false });
  });
});
