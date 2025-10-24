import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useTauriCommands, useTauriEvents, useKeyboardShortcuts, useWindowDrag } from './useTauri';
import { useAppStore } from '../store';

// Mock do Tauri API
vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn(),
}));

vi.mock('@tauri-apps/api/event', () => ({
  listen: vi.fn(),
}));

// Mock do store
vi.mock('../store', () => ({
  useAppStore: vi.fn(),
}));

// Mock console para evitar logs nos testes
const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

describe('useTauriCommands', () => {
  const mockStore = {
    setError: vi.fn(),
    setConnected: vi.fn(),
    setCurrentTrack: vi.fn(),
    setLyrics: vi.fn(),
    setSyncState: vi.fn(),
    setProgress: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAppStore).mockReturnValue(mockStore as any);
  });

  afterEach(() => {
    consoleSpy.mockClear();
  });

  describe('getCurrentTrack', () => {
    it('returns track data on success', async () => {
      const mockTrack = {
        name: 'Test Song',
        artist: 'Test Artist',
        album: { name: 'Test Album', images: [] },
        duration_ms: 180000,
        is_playing: true,
      };

      const { invoke } = await import('@tauri-apps/api/core');
      vi.mocked(invoke).mockResolvedValue(mockTrack);

      const { result } = renderHook(() => useTauriCommands());
      const track = await act(async () => {
        return await result.current.getCurrentTrack();
      });

      expect(invoke).toHaveBeenCalledWith('get_current_track');
      expect(mockStore.setConnected).toHaveBeenCalledWith(true);
      expect(track).toEqual(mockTrack);
    });

    it('handles error and sets error state', async () => {
      const { invoke } = await import('@tauri-apps/api/core');
      vi.mocked(invoke).mockRejectedValue(new Error('Connection failed'));

      const { result } = renderHook(() => useTauriCommands());
      const track = await act(async () => {
        return await result.current.getCurrentTrack();
      });

      expect(mockStore.setError).toHaveBeenCalledWith('Failed to connect to Spotify');
      expect(mockStore.setConnected).toHaveBeenCalledWith(false);
      expect(track).toBeNull();
    });

    it('returns null when no track is playing', async () => {
      const { invoke } = await import('@tauri-apps/api/core');
      vi.mocked(invoke).mockResolvedValue(null);

      const { result } = renderHook(() => useTauriCommands());
      const track = await act(async () => {
        return await result.current.getCurrentTrack();
      });

      expect(mockStore.setConnected).toHaveBeenCalledWith(true);
      expect(track).toBeNull();
    });
  });

  describe('getLyrics', () => {
    it('returns lyrics data on success', async () => {
      const mockLyrics = {
        blocks: [
          { start: 0, end: 1000, text: 'Test lyrics line' },
        ],
        quality: 'Synced',
      };

      const { invoke } = await import('@tauri-apps/api/core');
      vi.mocked(invoke).mockResolvedValue(mockLyrics);

      const { result } = renderHook(() => useTauriCommands());
      const lyrics = await act(async () => {
        return await result.current.getLyrics('Test Artist', 'Test Song');
      });

      expect(invoke).toHaveBeenCalledWith('get_lyrics', {
        artist: 'Test Artist',
        title: 'Test Song',
      });
      expect(lyrics).toEqual(mockLyrics);
    });

    it('handles error and sets error state', async () => {
      const { invoke } = await import('@tauri-apps/api/core');
      vi.mocked(invoke).mockRejectedValue(new Error('Lyrics not found'));

      const { result } = renderHook(() => useTauriCommands());
      const lyrics = await act(async () => {
        return await result.current.getLyrics('Unknown Artist', 'Unknown Song');
      });

      expect(mockStore.setError).toHaveBeenCalledWith('Failed to fetch lyrics');
      expect(lyrics).toBeNull();
    });

    it('returns null when no lyrics found', async () => {
      const { invoke } = await import('@tauri-apps/api/core');
      vi.mocked(invoke).mockResolvedValue(null);

      const { result } = renderHook(() => useTauriCommands());
      const lyrics = await act(async () => {
        return await result.current.getLyrics('Instrumental Artist', 'Instrumental Song');
      });

      expect(lyrics).toBeNull();
    });
  });

  describe('adjustOffset', () => {
    it('returns new offset on success', async () => {
      const { invoke } = await import('@tauri-apps/api/core');
      vi.mocked(invoke).mockResolvedValue(500);

      const { result } = renderHook(() => useTauriCommands());
      const newOffset = await act(async () => {
        return await result.current.adjustOffset(100);
      });

      expect(invoke).toHaveBeenCalledWith('adjust_offset', { delta: 100 });
      expect(newOffset).toBe(500);
    });

    it('handles error and returns 0', async () => {
      const { invoke } = await import('@tauri-apps/api/core');
      vi.mocked(invoke).mockRejectedValue(new Error('Adjust failed'));

      const { result } = renderHook(() => useTauriCommands());
      const newOffset = await act(async () => {
        return await result.current.adjustOffset(-200);
      });

      expect(mockStore.setError).toHaveBeenCalledWith('Failed to adjust offset');
      expect(newOffset).toBe(0);
    });

    it('handles positive and negative deltas', async () => {
      const { invoke } = await import('@tauri-apps/api/core');
      vi.mocked(invoke)
        .mockResolvedValueOnce(300) // +100 delta
        .mockResolvedValueOnce(-200); // -500 delta

      const { result } = renderHook(() => useTauriCommands());

      // Test positive delta
      const offset1 = await act(async () => {
        return await result.current.adjustOffset(100);
      });

      // Test negative delta
      const offset2 = await act(async () => {
        return await result.current.adjustOffset(-500);
      });

      expect(offset1).toBe(300);
      expect(offset2).toBe(-200);
    });
  });

  describe('resetOffset', () => {
    it('returns reset offset on success', async () => {
      const { invoke } = await import('@tauri-apps/api/core');
      vi.mocked(invoke).mockResolvedValue(0);

      const { result } = renderHook(() => useTauriCommands());
      const resetOffset = await act(async () => {
        return await result.current.resetOffset();
      });

      expect(invoke).toHaveBeenCalledWith('reset_offset');
      expect(resetOffset).toBe(0);
    });

    it('handles error and returns 0', async () => {
      const { invoke } = await import('@tauri-apps/api/core');
      vi.mocked(invoke).mockRejectedValue(new Error('Reset failed'));

      const { result } = renderHook(() => useTauriCommands());
      const resetOffset = await act(async () => {
        return await result.current.resetOffset();
      });

      expect(mockStore.setError).toHaveBeenCalledWith('Failed to reset offset');
      expect(resetOffset).toBe(0);
    });
  });

  describe('getSyncState', () => {
    it('returns sync state on success', async () => {
      const mockSyncState = {
        global_offset: 250,
        is_paused: false,
      };

      const { invoke } = await import('@tauri-apps/api/core');
      vi.mocked(invoke).mockResolvedValue(mockSyncState);

      const { result } = renderHook(() => useTauriCommands());
      const syncState = await act(async () => {
        return await result.current.getSyncState();
      });

      expect(invoke).toHaveBeenCalledWith('get_sync_state');
      expect(syncState).toEqual(mockSyncState);
    });

    it('handles error and returns null', async () => {
      const { invoke } = await import('@tauri-apps/api/core');
      vi.mocked(invoke).mockRejectedValue(new Error('Sync state failed'));

      const { result } = renderHook(() => useTauriCommands());
      const syncState = await act(async () => {
        return await result.current.getSyncState();
      });

      expect(mockStore.setError).toHaveBeenCalledWith('Failed to get sync state');
      expect(syncState).toBeNull();
    });
  });
});

describe('useTauriEvents', () => {
  const mockStore = {
    setCurrentTrack: vi.fn(),
    setLyrics: vi.fn(),
    setSyncState: vi.fn(),
    setProgress: vi.fn(),
    setError: vi.fn(),
    setConnected: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAppStore).mockReturnValue(mockStore as any);
  });

  it('sets up event listeners on mount', async () => {
    const { listen } = await import('@tauri-apps/api/event');
    const mockUnlisten = vi.fn();
    vi.mocked(listen).mockResolvedValue(mockUnlisten);

    renderHook(() => useTauriEvents());

    // Aguarda um tick para que os listeners sejam configurados
    await new Promise(resolve => setTimeout(resolve, 0));

    // Verifica se os listeners foram configurados (pode ser chamado em qualquer ordem)
    expect(listen).toHaveBeenCalledTimes(4);
    expect(listen).toHaveBeenCalledWith('track_changed', expect.any(Function));
    expect(listen).toHaveBeenCalledWith('lyrics_found', expect.any(Function));
    expect(listen).toHaveBeenCalledWith('progress_update', expect.any(Function));
    expect(listen).toHaveBeenCalledWith('sync_state_update', expect.any(Function));
  });

  it('handles track_changed event', async () => {
    const { listen } = await import('@tauri-apps/api/event');
    let trackChangedHandler: (event: any) => void = () => {};

    vi.mocked(listen).mockImplementation((eventName, handler) => {
      if (eventName === 'track_changed') {
        trackChangedHandler = handler;
      }
      return Promise.resolve(vi.fn());
    });

    renderHook(() => useTauriEvents());

    // Aguarda um tick para que os listeners sejam configurados
    await new Promise(resolve => setTimeout(resolve, 0));

    const mockTrack = {
      name: 'New Song',
      artist: 'New Artist',
      album: { name: 'New Album', images: [] },
      duration_ms: 200000,
      is_playing: true,
    };

    act(() => {
      trackChangedHandler({ payload: mockTrack });
    });

    expect(mockStore.setCurrentTrack).toHaveBeenCalledWith(mockTrack);
  });

  it('handles lyrics_found event', async () => {
    const { listen } = await import('@tauri-apps/api/event');
    let lyricsFoundHandler: (event: any) => void = () => {};

    vi.mocked(listen).mockImplementation((eventName, handler) => {
      if (eventName === 'lyrics_found') {
        lyricsFoundHandler = handler;
      }
      return Promise.resolve(vi.fn());
    });

    renderHook(() => useTauriEvents());

    // Aguarda um tick para que os listeners sejam configurados
    await new Promise(resolve => setTimeout(resolve, 0));

    const mockLyrics = {
      blocks: [{ start: 0, end: 1000, text: 'Event lyrics' }],
      quality: 'Synced',
    };

    act(() => {
      lyricsFoundHandler({ payload: mockLyrics });
    });

    expect(mockStore.setLyrics).toHaveBeenCalledWith(mockLyrics);
  });

  it('handles progress_update event', async () => {
    const { listen } = await import('@tauri-apps/api/event');
    let progressUpdateHandler: (event: any) => void = () => {};

    vi.mocked(listen).mockImplementation((eventName, handler) => {
      if (eventName === 'progress_update') {
        progressUpdateHandler = handler;
      }
      return Promise.resolve(vi.fn());
    });

    renderHook(() => useTauriEvents());

    // Aguarda um tick para que os listeners sejam configurados
    await new Promise(resolve => setTimeout(resolve, 0));

    const mockProgress = { progress_ms: 45000 };

    act(() => {
      progressUpdateHandler({ payload: mockProgress });
    });

    expect(mockStore.setProgress).toHaveBeenCalledWith(45000);
  });

  it('handles sync_state_update event', async () => {
    const { listen } = await import('@tauri-apps/api/event');
    let syncStateUpdateHandler: (event: any) => void = () => {};

    vi.mocked(listen).mockImplementation((eventName, handler) => {
      if (eventName === 'sync_state_update') {
        syncStateUpdateHandler = handler;
      }
      return Promise.resolve(vi.fn());
    });

    renderHook(() => useTauriEvents());

    // Aguarda um tick para que os listeners sejam configurados
    await new Promise(resolve => setTimeout(resolve, 0));

    const mockSyncState = {
      global_offset: 300,
      is_paused: true,
      current_track: null,
      lyrics: null
    };

    act(() => {
      syncStateUpdateHandler({ payload: mockSyncState });
    });

    expect(mockStore.setSyncState).toHaveBeenCalledWith(mockSyncState);
  });

  it('handles event listener setup errors', async () => {
    const { listen } = await import('@tauri-apps/api/event');
    
    // Mock listen para falhar
    vi.mocked(listen).mockRejectedValueOnce(new Error('Failed to setup listener'));

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    renderHook(() => useTauriEvents());

    // Aguarda um pouco para o erro ser processado
    await new Promise(resolve => setTimeout(resolve, 100));

    expect(consoleSpy).toHaveBeenCalledWith(
      'Failed to set up event listeners:',
      expect.any(Error)
    );

    consoleSpy.mockRestore();
  });
});

describe('useKeyboardShortcuts', () => {
  it('can be called without errors', () => {
    expect(() => {
      renderHook(() => useKeyboardShortcuts());
    }).not.toThrow();
  });
});

describe('useWindowDrag', () => {
  it('returns a ref object', () => {
    const { result } = renderHook(() => useWindowDrag());
    
    expect(result.current).toHaveProperty('current');
    expect(result.current.current).toBeNull();
  });

  it('can be called multiple times', () => {
    const { result: result1 } = renderHook(() => useWindowDrag());
    const { result: result2 } = renderHook(() => useWindowDrag());
    
    expect(result1.current).toHaveProperty('current');
    expect(result2.current).toHaveProperty('current');
  });
});
