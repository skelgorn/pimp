// Ultra minimalist floating lyrics - 3 verses only, 100% transparent background

import React, { useMemo, useState, useEffect } from 'react';
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

  // Calculate current block index with offset
  const currentBlockIndex = useMemo(() => {
    if (!lyrics || !lyrics.blocks || lyrics.blocks.length === 0) {
      console.log('⚠️ No lyrics blocks available');
      return -1;
    }

    const adjustedProgress = progress + syncState.global_offset;
    console.log('🎯 Progress calculation:', { progress, global_offset: syncState.global_offset, adjustedProgress });

    for (let i = 0; i < lyrics.blocks.length; i++) {
      const block = lyrics.blocks[i];
      if (adjustedProgress >= block.start && adjustedProgress < block.end) {
        console.log('🎯 Current block:', i, '-', block.text);
        return i;
      }
    }
    if (adjustedProgress < lyrics.blocks[0].start) {
      console.log('⏰ Waiting for first lyric at:', lyrics.blocks[0].start);
      return -1; // Aguardando primeira letra
    }
    console.log('🔚 At end of song');
    return lyrics.blocks.length - 1;
  }, [lyrics, progress, syncState.global_offset]);

  // Keyboard shortcuts para scroll manual (já que wheel não funciona com webkit drag)
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!lyrics?.blocks.length) return;

      let delta = 0;

      // Setas para scroll manual
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
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [lyrics, currentBlockIndex, manualScrollOffset]);

  // Handle different connection states
  if (!isConnected) {
    let msg = 'Connecting to Spotify...';
    if (error?.includes('token')) msg = 'Connect to Spotify';
    else if (error?.includes('private')) msg = 'Private session detected';
    else if (error?.includes('permission')) msg = 'Spotify permissions required';
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
          lineHeight: '1.6',
          background: 'transparent'
        }}
      >
        <div className="lyric-line previous"></div>
        <div className="lyric-line current">{msg}</div>
        <div className="lyric-line next"></div>
      </div>
    );
  }

  if (lyrics?.quality === 'Instrumental' || lyrics?.blocks.length === 0) {
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
          background: 'transparent'
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

  const threeLines = useMemo(() => {
    const effectiveIndex = currentBlockIndex + manualScrollOffset;

    // Se ainda não chegou na primeira letra (index -1) - FORÇAR EXIBIÇÃO PARA TESTE
    if (effectiveIndex < 0) {
      // TESTE: Mostrar primeira letra mesmo fora do tempo
      return {
        previous: '',
        current: lyrics?.blocks[0]?.text || 'No lyrics available',
        next: lyrics?.blocks[1]?.text || ''
      };
    }

    return {
      previous: effectiveIndex > 0 ? lyrics?.blocks[effectiveIndex - 1]?.text || '' : '',
      current: lyrics?.blocks[effectiveIndex]?.text || '',
      next: lyrics && lyrics.blocks && effectiveIndex < lyrics.blocks.length - 1 ? lyrics.blocks[effectiveIndex + 1]?.text || '' : ''
    };
  }, [lyrics, currentBlockIndex, manualScrollOffset]);

  return (
    <div>
      {/* DEBUG BLOCK - Remova depois de analisar */}
      <div style={{background: '#222', color: '#fff', fontSize: 12, padding: 8, marginBottom: 8, borderRadius: 8, opacity: 0.9}}>
        <div><b>DEBUG LyricsDisplay</b></div>
        <div>lyrics: {lyrics ? 'OK' : 'null'}</div>
        <div>lyrics.blocks.length: {lyrics?.blocks?.length ?? 'null'}</div>
        <div>currentBlockIndex: {currentBlockIndex}</div>
        <div>isConnected: {String(isConnected)}</div>
        <div>threeLines: {JSON.stringify(threeLines)}</div>
      </div>
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
        {/* Small drag handle - only this area allows dragging */}
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
                whiteSpace: 'pre-line',
                overflow: 'visible',
                width: 'auto',
                maxWidth: '95vw',
                lineHeight: 1.4
              }}
            >
              {threeLines.previous}
            </div>
            {/* Current line */}
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
                whiteSpace: 'pre-line',
                overflow: 'visible',
                width: 'auto',
                maxWidth: '95vw',
                lineHeight: 1.4
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
                whiteSpace: 'pre-line',
                overflow: 'visible',
                width: 'auto',
                maxWidth: '95vw',
                lineHeight: 1.4
              }}
            >
              {threeLines.next}
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
};
