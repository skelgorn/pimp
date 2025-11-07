// Custom hooks for Tauri backend communication (demo mode)

import { useCallback, useEffect, useRef } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { TrackInfo, LyricsData, SyncState } from '../types';
import { useAppStore } from '../store';

// 🎯 MODO HÍBRIDO - Tenta dados reais, fallback para simulação
const DEMO_MODE = false; // Sistema híbrido: real → simulação
// Hook for Tauri commands
export function useTauriCommands() {
  const { setError, setConnected } = useAppStore();

  const getCurrentTrack = useCallback(async (): Promise<TrackInfo | null> => {
    console.log('🔍 Calling get_current_track...');
    
    if (DEMO_MODE) {
      // 🎭 MODO HÍBRIDO - Tenta Spotify real, fallback para simulação
      console.log('🎭 DEMO MODE: Trying to get real Spotify data first...');
      
      try {
        const realTrack = await invoke<TrackInfo | null>('get_current_track');
        if (realTrack) {
          console.log('✅ DEMO MODE: Got real Spotify data!', realTrack);
          setConnected(true);
          return realTrack;
        }
      } catch (error) {
        console.log('⚠️ DEMO MODE: Real Spotify failed, using simulation:', error);
      }
      
      // Fallback para simulação se Spotify real falhar
      console.log('🎭 DEMO MODE: Using simulated track data');
      setConnected(true);
      return {
        id: 'demo-track-001',
        name: 'Bohemian Rhapsody',
        artist: 'Queen',
        album: {
          name: 'A Night at the Opera',
          images: [
            {
              url: 'https://i.scdn.co/image/ab67616d0000b273ce4f1737bc8a646c8c4bd25a',
              width: 640,
              height: 640
            }
          ]
        },
        duration_ms: 355000,
        is_playing: true,
        progress_ms: Math.floor(Date.now() / 10) % 355000 // Progresso simulado
      };
    }

    try {
      const track = await invoke<TrackInfo | null>('get_current_track');
      console.log('✅ get_current_track response:', track);
      setConnected(true);
      return track;
    } catch (error) {
      console.error('❌ Failed to get current track:', error);
      setError('Failed to connect to Spotify');
      return null;
    }
  }, [setError, setConnected]);

  const getLyrics = useCallback(async (artist: string, title: string): Promise<LyricsData | null> => {
    console.log(`🔍 getLyrics called for: "${title}" by ${artist}`);
    
    // 🎯 CRITICAL: ALWAYS try real backend first
    try {
      console.log('🎯 PRIORITY: Trying to get REAL lyrics from backend...');
      const realLyrics = await invoke<LyricsData | null>('get_lyrics', { artist, title });
      
      if (realLyrics && realLyrics.blocks && realLyrics.blocks.length > 0) {
        console.log(`✅ SUCCESS: Got ${realLyrics.blocks.length} REAL lyrics blocks from backend!`);
        console.log('📝 Real lyrics quality:', realLyrics.quality);
        console.log('📝 Real lyrics source:', realLyrics.source);
        return realLyrics;
      } else {
        console.log('⚠️ Backend returned null or empty lyrics');
      }
    } catch (error) {
      console.log('⚠️ Backend lyrics fetch failed:', error);
    }
    
    // Only use simulation if backend truly failed
    if (DEMO_MODE) {
      console.log('🎭 FALLBACK: Using simulated lyrics (backend had no real data)');
      
      const generateGenericLyrics = (songTitle: string, artistName: string) => {
        const lines = [
          `♪ ${songTitle} ♪`,
          `Performed by ${artistName}`,
          `This is a demo version`,
          `Real lyrics would appear here`,
          `When connected to the backend`,
          `🎵 Instrumental section 🎵`,
          `The music keeps playing`,
          `while we show this demo`,
          `Press ← → to adjust timing`,
          `Press R to reset offset`,
          `This simulates synchronized lyrics`,
          `For testing the interface`,
          `♪ ${songTitle} continues ♪`,
          `Thank you for testing!`,
          `🎵 End of demo lyrics 🎵`
        ];
        
        return lines.map((text, index) => ({
          start: index * 3000,
          end: (index + 1) * 3000,
          text
        }));
      };
      
      const simulatedLyrics: LyricsData = {
        blocks: generateGenericLyrics(title, artist),
        quality: 'Synced',
        source: 'Demo Mode - Simulated',
        confidence: 0.8
      };
      return simulatedLyrics;
    }
    
    console.log('❌ No lyrics available (neither real nor simulated)');
    setError('Failed to fetch lyrics');
    return null;
  }, [setError]);


  const resetOffset = useCallback(async (): Promise<number> => {
    try {
      const newOffset = await invoke<number>('reset_offset');
      return newOffset;
    } catch (error) {
      console.error('Failed to reset offset:', error);
      setError('Failed to reset offset');
      return 0;
    }
  }, [setError]);

  const getSyncState = useCallback(async (): Promise<SyncState | null> => {
    // 🎯 SEMPRE USA DADOS REAIS DO BACKEND
    try {
      const state = await invoke<SyncState>('get_sync_state');
      console.log('✅ SYNC STATE FROM BACKEND:', JSON.stringify(state, null, 2));
      
      // Debug detalhado
      if (state) {
        console.log('🔍 STATE DEBUG:');
        console.log('  - current_track:', state.current_track);
        console.log('  - lyrics:', state.lyrics);
        console.log('  - has lyrics blocks:', state.lyrics?.blocks?.length || 0);
      }
      
      // Se tem track real, usa os dados reais
      if (state && state.current_track && state.current_track.name !== 'Demo Song') {
        console.log('🎵 USING REAL TRACK DATA:', state.current_track.name, 'by', state.current_track.artist);
        return state;
      }
      
      // Se tem letras reais, usa mesmo sem track
      if (state && state.lyrics && state.lyrics.blocks && state.lyrics.blocks.length > 0) {
        console.log('📝 USING REAL LYRICS DATA:', state.lyrics.blocks.length, 'blocks');
        return state;
      }
      
      // SEMPRE retorna dados reais se existirem
      if (state && (state.current_track || state.lyrics)) {
        console.log('🎯 USING ANY REAL DATA AVAILABLE');
        return state;
      }
      
      // Fallback apenas se realmente não há dados
      if (DEMO_MODE) {
        console.log('🎭 DEMO MODE: No real data, using simulation');
        const simulatedState: SyncState = {
          current_track: {
            id: 'demo-track-123',
            name: 'Demo Song',
            artist: 'Demo Artist',
            album: {
              name: 'The Black Parade',
              images: [{
                url: 'https://i.scdn.co/image/ab67616d0000b273e65f0c2e5f0e0e0e0e0e0e0e',
                width: 640,
                height: 640
              }]
            },
            duration_ms: 60000,
            progress_ms: Date.now() % 60000,
            is_playing: true
          },
          current_block_index: Math.floor((Date.now() % 60000) / 3000),
          global_offset: 0,
          is_paused: false,
          user_has_scrolled: false
        };
        return simulatedState;
      }
      
      return state; // Retorna mesmo se vazio
    } catch (error) {
      console.error('❌ Failed to get sync state:', error);
      setError('Failed to get sync state');
      return null;
    }
  }, [setError]);

  const forceRefreshToken = useCallback(async (): Promise<void> => {
    if (DEMO_MODE) {
      console.log('🎭 DEMO MODE: Token refresh simulated');
      setConnected(true);
      return;
    }
    
    try {
      console.log('🔄 Forcing token refresh...');
      await invoke('force_refresh_token');
      console.log('✅ Token refreshed successfully');
      setConnected(true);
    } catch (error) {
      console.error('❌ Failed to refresh token:', error);
      throw error;
    }
  }, [setConnected, setError]);

  const clearLyricsCache = useCallback(async () => {
    if (DEMO_MODE) {
      console.log('🎭 DEMO MODE: Lyrics cache clear simulated');
      return;
    }
    
    try {
      await invoke('clear_lyrics_cache');
      console.log('✅ Lyrics cache cleared');
    } catch (error) {
      console.error('❌ Failed to clear lyrics cache:', error);
      setError('Failed to clear lyrics cache');
      throw error;
    }
  }, [setError]);

  // Advanced offset management functions
  const adjustOffset = useCallback(async (trackId: string, offsetDelta: number) => {
    if (DEMO_MODE) {
      console.log(`🎭 DEMO MODE: Offset adjusted by ${offsetDelta}ms for track ${trackId}`);
      return;
    }
    
    try {
      await invoke('adjust_offset', { trackId, offsetDelta });
      console.log(`✅ Offset adjusted by ${offsetDelta}ms for track ${trackId}`);
    } catch (error) {
      console.error('❌ Failed to adjust offset:', error);
      setError('Failed to adjust offset');
      throw error;
    }
  }, [setError]);

  const setAnchorOffset = useCallback(async (trackId: string, timestamp: number, offset: number) => {
    try {
      await invoke('set_anchor_offset', { trackId, timestamp, offset });
      console.log(`✅ Anchor offset set at ${timestamp}ms: ${offset}ms for track ${trackId}`);
    } catch (error) {
      console.error('❌ Failed to set anchor offset:', error);
      setError('Failed to set anchor offset');
      throw error;
    }
  }, []);

  const removeAnchorOffset = useCallback(async (trackId: string, timestamp: number) => {
    try {
      await invoke('remove_anchor_offset', { trackId, timestamp });
      console.log(`✅ Anchor offset removed at ${timestamp}ms for track ${trackId}`);
    } catch (error) {
      console.error('❌ Failed to remove anchor offset:', error);
      setError('Failed to remove anchor offset');
      throw error;
    }
  }, []);

  const resetTrackOffsets = useCallback(async (trackId: string) => {
    try {
      await invoke('reset_track_offsets', { trackId });
      console.log(`✅ All offsets reset for track ${trackId}`);
    } catch (error) {
      console.error('❌ Failed to reset track offsets:', error);
      setError('Failed to reset track offsets');
      throw error;
    }
  }, []);

  const getTrackAnchors = useCallback(async (trackId: string) => {
    try {
      const anchors = await invoke('get_track_anchors', { trackId });
      console.log(`✅ Retrieved ${Array.isArray(anchors) ? anchors.length : 0} anchors for track ${trackId}`);
      return anchors;
    } catch (error) {
      console.error('❌ Failed to get track anchors:', error);
      setError('Failed to get track anchors');
      throw error;
    }
  }, []);

  const getCurrentOffset = useCallback(async (trackId: string, timestamp: number) => {
    try {
      const offset = await invoke('get_current_offset', { trackId, timestamp });
      return offset as number;
    } catch (error) {
      console.error('❌ Failed to get current offset:', error);
      setError('Failed to get current offset');
      throw error;
    }
  }, []);

  return {
    getCurrentTrack,
    getLyrics,
    adjustOffset,
    resetOffset,
    getSyncState,
    forceRefreshToken,
    clearLyricsCache,
    setAnchorOffset,
    removeAnchorOffset,
    resetTrackOffsets,
    getTrackAnchors,
    getCurrentOffset,
  };
}

// Hook for real-time updates from backend
export function useTauriEvents() {
  const {
    setCurrentTrack,
    setLyrics,
    setSyncState,
    setProgress,
    setError,
    setConnected,
  } = useAppStore();

  const { getCurrentTrack, getLyrics, getSyncState, forceRefreshToken } = useTauriCommands();

  useEffect(() => {
    console.log('🎵 FRONTEND: Starting real-time sync with backend...');
    console.log('🎭 DEMO_MODE status:', DEMO_MODE);
    
    let isActive = true;
    let lastTrackId: string | null = null;
    let noDevicesCount = 0;
    let lastRefreshAttempt = 0;

    // Main polling loop
    const startPolling = async () => {
      while (isActive) {
        try {
          // Get current track from Spotify
          const currentTrack = await getCurrentTrack();
          console.log('🎵 Polling result:', currentTrack ? `Track: ${currentTrack.name} - Playing: ${currentTrack.is_playing}` : 'NULL');
          
          if (currentTrack) {
            console.log('✅ TRACK DETECTED - ID:', currentTrack.id, 'Name:', currentTrack.name);
            // Mark as connected when we get track data
            setConnected(true);
            setError(null);
            
            // Update progress
            setProgress(currentTrack.progress_ms);
            
            // Always update sync state to catch play/pause changes
            const syncState = await getSyncState();
            if (syncState) {
              console.log('🎮 Sync state - is_paused:', syncState.is_paused, 'is_playing:', currentTrack.is_playing);
              setSyncState(syncState);
            }
            
            // Check if track changed OR if it's the first time
            if (currentTrack.id !== lastTrackId || lastTrackId === null) {
              console.log('🔄 Track changed:', currentTrack.name, 'by', currentTrack.artist);
              lastTrackId = currentTrack.id;
              setCurrentTrack(currentTrack);
              
              // 🎯 CRITICAL FIX: Check for real lyrics in syncState FIRST
              if (syncState?.lyrics && syncState.lyrics.blocks && syncState.lyrics.blocks.length > 0) {
                console.log(`✅ USING REAL LYRICS from backend: ${syncState.lyrics.blocks.length} blocks`);
                console.log('📝 Lyrics quality:', syncState.lyrics.quality);
                console.log('📝 Lyrics source:', syncState.lyrics.source);
                console.log('📝 First lyric:', syncState.lyrics.blocks[0]?.text);
                setLyrics(syncState.lyrics);
              } else {
                // Only fetch if syncState has no lyrics
                console.log('⚠️ No lyrics in syncState, fetching via getLyrics...');
                const fetchedLyrics = await getLyrics(currentTrack.artist, currentTrack.name);
                
                if (fetchedLyrics && fetchedLyrics.blocks.length > 0) {
                  console.log(`📝 Fetched lyrics: ${fetchedLyrics.blocks.length} blocks`);
                  console.log('📝 Source:', fetchedLyrics.source);
                  setLyrics(fetchedLyrics);
                } else {
                  console.log('❌ No lyrics found');
                  setLyrics(null);
                }
              }
            }
          } else {
            // No track playing - check if we should use demo mode
            if (DEMO_MODE && lastTrackId === null) {
              console.log('🎭 DEMO MODE: Backend returned null, activating simulation...');
              
              const simulatedTrack = {
                id: 'demo-track-001',
                name: 'Bohemian Rhapsody',
                artist: 'Queen',
                album: {
                  name: 'A Night at the Opera',
                  images: [
                    {
                      url: 'https://i.scdn.co/image/ab67616d0000b273ce4f1737bc8a646c8c4bd25a',
                      width: 640,
                      height: 640
                    }
                  ]
                },
                duration_ms: 355000,
                is_playing: true,
                progress_ms: Math.floor(Date.now() / 10) % 355000
              };
              
              console.log('🎵 DEMO: Setting simulated track:', simulatedTrack.name, 'by', simulatedTrack.artist);
              lastTrackId = simulatedTrack.id;
              setCurrentTrack(simulatedTrack);
              setProgress(simulatedTrack.progress_ms);
              
              // Fetch lyrics for simulated track
              const lyrics = await getLyrics(simulatedTrack.artist, simulatedTrack.name);
              if (lyrics) {
                console.log('📝 DEMO: Lyrics loaded:', lyrics.blocks.length, 'blocks');
                setLyrics(lyrics);
              } else {
                console.log('❌ DEMO: No lyrics found, using fallback');
                setLyrics(null);
              }
              
              // Set sync state for demo
              setSyncState({
                is_paused: false,
                global_offset: 0,
                user_has_scrolled: false
              });
              
            } else {
              // No track playing - increment counter for potential token refresh
              console.log('❌ NO TRACK DETECTED - currentTrack is null/undefined');
              noDevicesCount++;
              
              if (lastTrackId !== null) {
                console.log('⏹️ No track playing - BUT KEEPING LYRICS FOR NOW (lastTrackId was:', lastTrackId, ')');
                // NÃO limpar as letras imediatamente - manter para visualização
                // lastTrackId = null;
                // setCurrentTrack(null);
                // setLyrics(null);
                // setProgress(0);
              } else {
                console.log('⏹️ Still no track playing (noDevicesCount:', noDevicesCount, ')');
              }
              
              // Try token refresh if no devices detected for too long
              const now = Date.now();
              if (noDevicesCount >= 10 && (now - lastRefreshAttempt) > 30000) { // 10 attempts, 30s cooldown
                console.log('🔄 No devices detected for too long, attempting token refresh...');
                lastRefreshAttempt = now;
                noDevicesCount = 0; // Reset counter
                
                try {
                  await forceRefreshToken();
                  console.log('✅ Token refresh successful, continuing polling...');
                } catch (error) {
                  console.log('❌ Token refresh failed:', error);
                }
              }
            }
          }
          
          setConnected(true);
          setError(null);
          
        } catch (error) {
          console.error('🔥 Polling error:', error);
          console.error('🔥 Error details:', error);
          setConnected(false);
          setError(`Connection lost: ${error}`);
        }
        
        // Wait before next poll
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    };

    // Start polling
    startPolling();

    // Cleanup
    return () => {
      isActive = false;
    };
  }, [getCurrentTrack, getLyrics, getSyncState, setCurrentTrack, setLyrics, setSyncState, setProgress, setError, setConnected]);
}

// Hook for keyboard shortcuts (simplified for demo)
export function useKeyboardShortcuts() {
  const { adjustOffset, resetOffset, clearLyricsCache, getCurrentTrack } = useTauriCommands();

  // Function to handle lyrics refresh
  const handleLyricsRefresh = useCallback(async () => {
    try {
      console.log('🔄 CTRL+L PRESSED - Refreshing lyrics...');
      
      // Get current track info
      const track = await getCurrentTrack();
      if (!track) {
        console.log('❌ No track playing');
        alert('❌ Nenhuma música tocando no Spotify');
        return;
      }

      console.log(`🎵 Current track: ${track.artist} - ${track.name}`);

      // Clear cache for current track
      await clearLyricsCache();
      console.log('🗑️ Lyrics cache cleared');

      // Force page reload to trigger new lyrics search
      console.log('🔄 Reloading page to force new lyrics search...');
      window.location.reload();
      
    } catch (error) {
      console.error('❌ Failed to refresh lyrics:', error);
      alert('❌ Erro ao atualizar letras: ' + error);
    }
  }, [getCurrentTrack, clearLyricsCache]);

  // Function to handle offset adjustment
  const handleOffsetAdjustment = useCallback(async (delta: number) => {
    try {
      const track = await getCurrentTrack();
      if (!track) {
        console.log('❌ No track playing for offset adjustment');
        return;
      }

      console.log(`🎯 Adjusting offset by ${delta}ms for track: ${track.artist} - ${track.name}`);
      await adjustOffset(track.id, delta);
      
      console.log(`✅ Offset adjusted by ${delta}ms`);
      
    } catch (error) {
      console.error('❌ Failed to adjust offset:', error);
    }
  }, [getCurrentTrack, adjustOffset]);

  // Function to handle reset offset
  const handleResetOffset = useCallback(async () => {
    try {
      const track = await getCurrentTrack();
      if (!track) {
        console.log('❌ No track playing for reset offset');
        return;
      }

      console.log(`🔄 Resetting offset for track: ${track.artist} - ${track.name}`);
      await resetOffset();
      
      console.log(`✅ Offset reset successfully`);
      
    } catch (error) {
      console.error('❌ Failed to reset offset:', error);
    }
  }, [getCurrentTrack, resetOffset]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Ignore if user is typing in an input
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
        return;
      }

      // Handle Ctrl+L for lyrics refresh
      if (event.ctrlKey && event.key === 'l') {
        console.log('🎯 CTRL+L detected!');
        event.preventDefault();
        handleLyricsRefresh();
        return;
      }

      // Handle Left Arrow for -100ms offset
      if (event.key === 'ArrowLeft' && !event.ctrlKey && !event.shiftKey) {
        console.log('🎯 LEFT ARROW - Decreasing offset by 100ms');
        event.preventDefault();
        handleOffsetAdjustment(-100);
        return;
      }

      // Handle Right Arrow for +100ms offset
      if (event.key === 'ArrowRight' && !event.ctrlKey && !event.shiftKey) {
        console.log('🎯 RIGHT ARROW - Increasing offset by 100ms');
        event.preventDefault();
        handleOffsetAdjustment(100);
        return;
      }

      // Handle Shift+Left Arrow for -500ms offset
      if (event.key === 'ArrowLeft' && event.shiftKey) {
        console.log('🎯 SHIFT+LEFT ARROW - Decreasing offset by 500ms');
        event.preventDefault();
        handleOffsetAdjustment(-500);
        return;
      }

      // Handle Shift+Right Arrow for +500ms offset
      if (event.key === 'ArrowRight' && event.shiftKey) {
        console.log('🎯 SHIFT+RIGHT ARROW - Increasing offset by 500ms');
        event.preventDefault();
        handleOffsetAdjustment(500);
        return;
      }

      // Handle R for reset offset
      if (event.key === 'r' && !event.ctrlKey && !event.shiftKey) {
        console.log('🎯 R KEY - Resetting offset');
        event.preventDefault();
        handleResetOffset();
        return;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleLyricsRefresh, handleOffsetAdjustment, handleResetOffset]);
}

// Hook for window drag functionality using Tauri API (deprecated - using direct API in App.tsx)
export function useWindowDrag() {
  const dragRef = useRef<HTMLDivElement>(null);
  // This hook is no longer used but kept for compatibility
  console.log('useWindowDrag hook called but deprecated');
  
  return dragRef;
}