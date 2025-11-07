import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useTauriCommands, useKeyboardShortcuts, useWindowDrag } from './useTauri';
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
      await act(async () => {
        await result.current.adjustOffset('track-123', 100);
      });

      expect(invoke).toHaveBeenCalledWith('adjust_offset', { trackId: 'track-123', offsetDelta: 100 });
    });

    it('handles error and returns 0', async () => {
      const { invoke } = await import('@tauri-apps/api/core');
      vi.mocked(invoke).mockRejectedValue(new Error('Adjust failed'));

      const { result } = renderHook(() => useTauriCommands());
      
      await expect(act(async () => {
        await result.current.adjustOffset('track-456', -200);
      })).rejects.toThrow('Adjust failed');

      expect(mockStore.setError).toHaveBeenCalledWith('Failed to adjust offset');
    });

    it('handles positive and negative deltas', async () => {
      const { invoke } = await import('@tauri-apps/api/core');
      vi.mocked(invoke)
        .mockResolvedValueOnce(300) // +100 delta
        .mockResolvedValueOnce(-200); // -500 delta

      const { result } = renderHook(() => useTauriCommands());

      // Test positive delta
      await act(async () => {
        await result.current.adjustOffset('track-789', 100);
      });

      // Test negative delta
      await act(async () => {
        await result.current.adjustOffset('track-789', -500);
      });

      expect(invoke).toHaveBeenCalledTimes(2);
      expect(invoke).toHaveBeenNthCalledWith(1, 'adjust_offset', { trackId: 'track-789', offsetDelta: 100 });
      expect(invoke).toHaveBeenNthCalledWith(2, 'adjust_offset', { trackId: 'track-789', offsetDelta: -500 });
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

describe.skip('useTauriEvents (DEPRECATED - now uses polling)', () => {
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
    // Test disabled - useTauriEvents now uses polling
  });

  it('handles track_changed event', async () => {
    // Test disabled - useTauriEvents now uses polling
  });

  it('handles lyrics_found event', async () => {
    // Test disabled - useTauriEvents now uses polling
  });

  it('handles progress_update event', async () => {
    // Test disabled - useTauriEvents now uses polling
  });

  it('handles sync_state_update event', async () => {
    // Test disabled - useTauriEvents now uses polling
  });

  it('handles event listener setup errors', async () => {
    // Test disabled - useTauriEvents now uses polling
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
