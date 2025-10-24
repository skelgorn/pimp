// Ultra minimalist floating lyrics - 3 verses only, 100% transparent background
// 🔧 FIXED: Proper lyrics detection and rendering

import React, { useMemo, useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore, selectLyrics, selectSyncState, selectProgress, selectIsConnected, selectError } from '../store';

interface LyricsDisplayProps {
  // No props needed for ultra minimalist design
}

export const LyricsDisplay: React.FC<LyricsDisplayProps> = () => {
  const lyrics = useAppStore(selectLyrics);
  const syncState = useAppStore(selectSyncState);
  const progress = useAppStore(selectProgress);
  const isConnected = useAppStore(selectIsConnected);
  const error = useAppStore(selectError);

  const [manualScrollOffset, setManualScrollOffset] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  // 🔍 DEBUG: Log state changes
  useEffect(() => {
    console.log('🎵 LyricsDisplay State Update:');
    console.log('  - isConnected:', isConnected);
    console.log('  - lyrics:', lyrics);
    console.log('  - lyrics?.blocks?.length:', lyrics?.blocks?.length);
    console.log('  - syncState:', syncState);
    console.log('  - progress:', progress);
  }, [lyrics, isConnected, syncState, progress]);

  // Calculate current block index with offset
  const currentBlockIndex = useMemo(() => {
    if (!lyrics || !lyrics.blocks || lyrics.blocks.length === 0) {
      console.log('⚠️ No lyrics blocks available');
      return -1;
    }
    
    const adjustedProgress = progress + syncState.global_offset;
    
    for (let i = 0; i < lyrics.blocks.length; i++) {
      const block = lyrics.blocks[i];
      if (adjustedProgress >= block.start && adjustedProgress < block.end) {
        console.log(`🎯 Current block: ${i} - "${block.text}"`);
        return i;
      }
    }
    
    if (adjustedProgress < lyrics.blocks[0].start) {
      console.log('⏰ Before first lyric');
      return -1;
    }
    
    console.log('🏁 After last lyric');
    return lyrics.blocks.length - 1;
  }, [lyrics, progress, syncState.global_offset]);

  // Keyboard shortcuts for manual scroll
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!lyrics?.blocks?.length) return;
      
      let delta = 0;
      
      if (event.key === 'ArrowUp') {
        delta = -1;
        event.preventDefault();
      } else if (event.key === 'ArrowDown') {
        delta = 1;
        event.preventDefault();
      }
      
      if (delta !== 0) {
        const newOffset = Math.max(
          -currentBlockIndex,
          Math.min(
            lyrics.blocks.length - 1 - currentBlockIndex,
            manualScrollOffset + delta
          )
        );
        setManualScrollOffset(newOffset);
        console.log(`📜 Manual scroll offset: ${newOffset}`);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [lyrics, currentBlockIndex, manualScrollOffset]);

  // Get the 3 lines to display (always 3 lines)
  const getThreeLines = () => {
    // 🔍 CRITICAL FIX: Proper null/undefined checks
    const hasLyrics = lyrics && lyrics.blocks && Array.isArray(lyrics.blocks) && lyrics.blocks.length > 0;
    
    console.log('🔍 getThreeLines check:', {
      hasLyrics,
      lyricsIsNull: lyrics === null,
      lyricsIsUndefined: lyrics === undefined,
      blocksLength: lyrics?.blocks?.length,
      isConnected
    });

    if (!hasLyrics) {
      if (isConnected) {
        console.log('⏳ Connected but no lyrics - loading...');
        return {
          previous: '',
          current: 'Loading lyrics...',
          next: ''
        };
      }
      console.log('⏸️ Not connected - waiting...');
      return {
        previous: '',
        current: 'Waiting for music...',
        next: ''
      };
    }
    
    console.log('✅ Has lyrics! Blocks:', lyrics.blocks.length);
    
    const effectiveIndex = currentBlockIndex + manualScrollOffset;
    
    // Before first lyric - show track info + first line
    if (effectiveIndex < 0) {
      const trackName = syncState.current_track?.name || 'Unknown Track';
      const artistName = syncState.current_track?.artist || 'Unknown Artist';
      
      console.log(`🎵 Before first lyric: ${artistName} - ${trackName}`);
      
      return {
        previous: `🎵 ${artistName} - ${trackName}`,
        current: lyrics.blocks[0]?.text || 'No lyrics available',
        next: lyrics.blocks[1]?.text || ''
      };
    }
    
    // Normal playback
    const lines = {
      previous: effectiveIndex > 0 ? lyrics.blocks[effectiveIndex - 1]?.text || '' : '',
      current: lyrics.blocks[effectiveIndex]?.text || '',
      next: effectiveIndex < lyrics.blocks.length - 1 ? lyrics.blocks[effectiveIndex + 1]?.text || '' : ''
    };
    
    console.log('📝 Displaying lines:', lines);
    return lines;
  };

  const threeLines = getThreeLines();

  // Handle not connected state
  if (!isConnected) {
    const getConnectionMessage = () => {
      if (error?.includes('token')) return 'Connect to Spotify';
      if (error?.includes('private')) return 'Private session detected';
      if (error?.includes('permission')) return 'Spotify permissions required';
      return 'Connecting to Spotify...';
    };

    return (
      <div
        className="floating-lyrics-container"
        style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 9999,
          pointerEvents: 'none',
          userSelect: 'none',
          fontFamily: 'Segoe UI, system-ui, sans-serif',
          color: '#ffffff',
          textShadow: '2px 2px 4px rgba(0,0,0,0.8)',
          textAlign: 'center',
          fontSize: '18px',
          lineHeight: '1.6'
        }}
      >
        <div className="lyric-line previous"></div>
        <div className="lyric-line current">{getConnectionMessage()}</div>
        <div className="lyric-line next"></div>
      </div>
    );
  }

  // Handle instrumental track
  if (lyrics && (lyrics.quality === 'Instrumental' || lyrics.blocks.length === 0)) {
    return (
      <div
        className="floating-lyrics-container"
        style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 10000,
          pointerEvents: 'auto',
          userSelect: 'none',
          WebkitUserSelect: 'none',
          MozUserSelect: 'none',
          msUserSelect: 'none'
        }}
      >
        <div className="lyric-line previous"></div>
        <div className="lyric-line current instrumental">🎵 Instrumental Track 🎵</div>
        <div className="lyric-line next"></div>
      </div>
    );
  }

  // Handle paused state
  if (syncState?.is_paused) {
    return (
      <div
        className="floating-lyrics-container"
        style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 10000,
          pointerEvents: 'none',
          userSelect: 'none',
          WebkitUserSelect: 'none',
          MozUserSelect: 'none',
          msUserSelect: 'none'
        }}
      >
        <div
          data-tauri-drag-region
          style={{
            position: 'absolute',
            top: '-10px',
            left: '50%',
            transform: 'translateX(-50%)',
            width: '40px',
            height: '20px',
            pointerEvents: 'auto',
            cursor: 'move',
            background: 'rgba(255, 255, 255, 0.1)',
            borderRadius: '10px',
            opacity: 0,
            transition: 'opacity 0.2s'
          }}
          onMouseEnter={(e) => e.currentTarget.style.opacity = '0.3'}
          onMouseLeave={(e) => e.currentTarget.style.opacity = '0'}
        />
        
        <div className="lyric-line previous"></div>
        <div className="lyric-line current paused">⏸️ Música Pausada</div>
        <div className="lyric-line next"></div>
      </div>
    );
  }

  // Normal state - SHOW LYRICS!
  return (
    <div
      ref={containerRef}
      className="floating-lyrics-container"
      style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: 'fit-content',
        maxWidth: '90%',
        zIndex: 10000,
        pointerEvents: 'auto',
        background: 'rgba(0, 0, 0, 0.01)',
        userSelect: 'none',
        WebkitUserSelect: 'none',
        MozUserSelect: 'none',
        msUserSelect: 'none'
      }}>
      
      {/* Drag handle */}
      <div
        data-tauri-drag-region
        style={{
          position: 'absolute',
          top: '-10px',
          left: '50%',
          transform: 'translateX(-50%)',
          width: '40px',
          height: '20px',
          pointerEvents: 'auto',
          cursor: 'move',
          background: 'rgba(255, 255, 255, 0.1)',
          borderRadius: '10px',
          opacity: 0,
          transition: 'opacity 0.2s'
        }}
        onMouseEnter={(e) => e.currentTarget.style.opacity = '0.3'}
        onMouseLeave={(e) => e.currentTarget.style.opacity = '0'}
      />
      
      <AnimatePresence mode="wait">
        <motion.div
          key={`${currentBlockIndex}-${manualScrollOffset}`}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.3 }}
          style={{ textAlign: 'center' }}
        >
          {/* Previous line */}
          <div
            className="lyric-line previous"
            style={{
              color: 'rgba(255, 255, 255, 0.5)',
              fontSize: '14px',
              fontWeight: '400',
              textShadow: '2px 2px 4px rgba(0, 0, 0, 0.8)',
              marginBottom: '4px',
              minHeight: '18px',
              pointerEvents: 'none',
              userSelect: 'none',
              WebkitUserSelect: 'none',
              MozUserSelect: 'none',
              msUserSelect: 'none',
            }}
          >
            {threeLines.previous}
          </div>
          
          {/* Current line - HIGHLIGHTED */}
          <div
            className="lyric-line current"
            style={{
              color: 'rgba(255, 255, 255, 1)',
              fontSize: '24px',
              fontWeight: '700',
              textShadow: '3px 3px 6px rgba(0, 0, 0, 0.9)',
              marginBottom: '8px',
              minHeight: '32px',
              transform: 'scale(1.1)',
              pointerEvents: 'none',
              userSelect: 'none',
              WebkitUserSelect: 'none',
              MozUserSelect: 'none',
              msUserSelect: 'none',
            }}
          >
            {threeLines.current}
          </div>
          
          {/* Next line */}
          <div
            className="lyric-line next"
            style={{
              color: 'rgba(255, 255, 255, 0.6)',
              fontSize: '18px',
              fontWeight: '400',
              textShadow: '2px 2px 4px rgba(0, 0, 0, 0.8)',
              minHeight: '24px',
              pointerEvents: 'none',
              userSelect: 'none',
              WebkitUserSelect: 'none',
              MozUserSelect: 'none',
              msUserSelect: 'none',
            }}
          >
            {threeLines.next}
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
};