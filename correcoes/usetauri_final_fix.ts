// Custom hooks for Tauri backend communication
// 🔧 FIXED: Always prioritize real lyrics from backend over simulation

import { useCallback, useEffect, useRef } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { TrackInfo, LyricsData, SyncState } from '../types';
import { useAppStore } from '../store';

const DEMO_MODE = true; // Hybrid mode for track detection fallback

export function useTauriCommands() {
  const { setError, setConnected } = useAppStore();

  const getCurrentTrack = useCallback(async (): Promise<TrackInfo | null> => {
    console.log('🔍 Calling get_current_track...');
    
    if (DEMO_MODE) {
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
      
      // Fallback to simulation
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
        progress_ms: Math.floor(Date.now() / 10) % 355000
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
      setConnected(false);
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
          `While we show this demo`,
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
    try {
      const state = await invoke<SyncState>('get_sync_state');
      console.log('✅ SYNC STATE FROM BACKEND:', state);
      
      if (state) {
        console.log('🔍 STATE DEBUG:');
        console.log('  - current_track:', state.current_track?.name, 'by', state.current_track?.artist);
        console.log('  - has lyrics:', !!state.lyrics);
        console.log('  - lyrics blocks:', state.lyrics?.blocks?.length || 0);
        console.log('  - global_offset:', state.global_offset);
        console.log('  - is_paused:', state.is_paused);
      }
      
      return state;
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
  }, [setConnected]);

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
  }, [setError]);

  const removeAnchorOffset = useCallback(async (trackId: string, timestamp: number) => {
    try {
      await invoke('remove_anchor_offset', { trackId, timestamp });
      console.log(`✅ Anchor offset removed at ${timestamp}ms for track ${trackId}`);
    } catch (error) {
      console.error('❌ Failed to remove anchor offset:', error);
      setError('Failed to remove anchor offset');
      throw error;
    }
  }, [setError]);

  const resetTrackOffsets = useCallback(async (trackId: string) => {
    try {
      await invoke('reset_track_offsets', { trackId });
      console.log(`✅ All offsets reset for track ${trackId}`);
    } catch (error) {
      console.error('❌ Failed to reset track offsets:', error);
      setError('Failed to reset track offsets');
      throw error;
    }
  }, [setError]);

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
  }, [setError]);

  const getCurrentOffset = useCallback(async (trackId: string, timestamp: number) => {
    try {
      const offset = await invoke('get_current_offset', { trackId, timestamp });
      return offset as number;
    } catch (error) {
      console.error('❌ Failed to get current offset:', error);
      setError('Failed to get current offset');
      throw error;
    }
  }, [setError]);

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

  const { getCurrentTrack, getLyrics, getSyncState } = useTauriCommands();

  useEffect(() => {
    console.log('🎵 FRONTEND: Starting real-time sync with backend...');
    console.log('🎭 DEMO_MODE status:', DEMO_MODE);
    
    let isActive = true;
    let lastTrackId: string | null = null;

    const startPolling = async () => {
      while (isActive) {
        try {
          // Get current track
          const currentTrack = await getCurrentTrack();
          console.log('🎵 Polling result:', currentTrack?.name, 'by', currentTrack?.artist);
          
          if (currentTrack) {
            setConnected(true);
            setError(null);
            setProgress(currentTrack.progress_ms);
            
            // Get sync state (contains real lyrics!)
            const syncState = await getSyncState();
            console.log('🎮 Sync state retrieved:', {
              hasLyrics: !!syncState?.lyrics,
              lyricsBlocks: syncState?.lyrics?.blocks?.length || 0
            });
            
            if (syncState) {
              setSyncState(syncState);
            }
            
            // Track changed detection
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
            } else {
              // Same track - still update sync state for progress
              if (syncState) {
                setSyncState(syncState);
              }
            }
          } else {
            // No track - try demo mode
            if (DEMO_MODE && lastTrackId === null) {
              console.log('🎭 DEMO MODE: Activating simulation...');
              
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
              
              lastTrackId = simulatedTrack.id;
              setCurrentTrack(simulatedTrack);
              setProgress(simulatedTrack.progress_ms);
              
              const lyrics = await getLyrics(simulatedTrack.artist, simulatedTrack.name);
              if (lyrics) {
                setLyrics(lyrics);
              }
              
              setSyncState({
                current_block_index: -1,
                is_paused: false,
                global_offset: 0,
                user_has_scrolled: false
              });
            } else {
              if (lastTrackId !== null) {
                console.log('ℹ️ No track playing');
                lastTrackId = null;
                setCurrentTrack(null);
                setLyrics(null);
                setProgress(0);
              }
            }
          }
          
          setConnected(true);
          
        } catch (error) {
          console.error('🔥 Polling error:', error);
          setConnected(false);
          setError(`Connection lost: ${error}`);
        }
        
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    };

    startPolling();

    return () => {
      isActive = false;
    };
  }, [getCurrentTrack, getLyrics, getSyncState, setCurrentTrack, setLyrics, setSyncState, setProgress, setError, setConnected]);
}

// Hook for keyboard shortcuts
export function useKeyboardShortcuts() {
  const { adjustOffset, resetOffset, clearLyricsCache, getCurrentTrack } = useTauriCommands();

  const handleLyricsRefresh = useCallback(async () => {
    try {
      console.log('🔄 CTRL+L PRESSED - Refreshing lyrics...');
      
      const track = await getCurrentTrack();
      if (!track) {
        console.log('❌ No track playing');
        alert('❌ Nenhuma música tocando no Spotify');
        return;
      }

      console.log(`🎵 Current track: ${track.artist} - ${track.name}`);
      await clearLyricsCache();
      console.log('🗑️ Lyrics cache cleared');
      console.log('🔄 Reloading page to force new lyrics search...');
      window.location.reload();
      
    } catch (error) {
      console.error('❌ Failed to refresh lyrics:', error);
      alert('❌ Erro ao atualizar letras: ' + error);
    }
  }, [getCurrentTrack, clearLyricsCache]);

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
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
        return;
      }

      if (event.ctrlKey && event.key === 'l') {
        console.log('🎯 CTRL+L detected!');
        event.preventDefault();
        handleLyricsRefresh();
        return;
      }

      if (event.key === 'ArrowLeft' && !event.ctrlKey && !event.shiftKey) {
        console.log('🎯 LEFT ARROW - Decreasing offset by 100ms');
        event.preventDefault();
        handleOffsetAdjustment(-100);
        return;
      }

      if (event.key === 'ArrowRight' && !event.ctrlKey && !event.shiftKey) {
        console.log('🎯 RIGHT ARROW - Increasing offset by 100ms');
        event.preventDefault();
        handleOffsetAdjustment(100);
        return;
      }

      if (event.key === 'ArrowLeft' && event.shiftKey) {
        console.log('🎯 SHIFT+LEFT ARROW - Decreasing offset by 500ms');
        event.preventDefault();
        handleOffsetAdjustment(-500);
        return;
      }

      if (event.key === 'ArrowRight' && event.shiftKey) {
        console.log('🎯 SHIFT+RIGHT ARROW - Increasing offset by 500ms');
        event.preventDefault();
        handleOffsetAdjustment(500);
        return;
      }

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

export function useWindowDrag() {
  const dragRef = useRef<HTMLDivElement>(null);
  console.log('useWindowDrag hook called but deprecated');
  return dragRef;
}