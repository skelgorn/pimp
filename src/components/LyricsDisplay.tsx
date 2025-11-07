// Ultra minimalist floating lyrics - 3 verses only, 100% transparent background

import React, { useMemo, useState, useEffect } from 'react';
import { useAppStore, selectLyrics, selectSyncState, selectProgress, selectIsConnected } from '../store';

interface LyricsDisplayProps {
  // No props needed for ultra minimalist design
}

export const LyricsDisplay: React.FC<LyricsDisplayProps> = () => {
  const lyrics = useAppStore(selectLyrics);
  const syncState = useAppStore(selectSyncState);
  const progress = useAppStore(selectProgress);
  const isConnected = useAppStore(selectIsConnected);

  // LOG AGRESSIVO PARA DEBUG
  console.log('🔍 LyricsDisplay RENDER:', {
    hasLyrics: !!lyrics,
    blocksCount: lyrics?.blocks?.length ?? 0,
    progress,
    isConnected,
    isPaused: syncState?.is_paused,
    lyricsObject: lyrics ? { quality: lyrics.quality, source: lyrics.source } : null
  });

  // LOG QUANDO COMPONENTE É DESMONTADO
  useEffect(() => {
    console.log('✅ LyricsDisplay MOUNTED');
    return () => {
      console.log('❌ LyricsDisplay UNMOUNTED - Component being destroyed!');
    };
  }, []);

  // LOG QUANDO LYRICS MUDAM
  useEffect(() => {
    console.log('🔄 LYRICS CHANGED:', lyrics ? `${lyrics.blocks?.length} blocks` : 'NULL');
  }, [lyrics]);

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
      console.log('⏰ Waiting for first lyric at:', lyrics.blocks[0].start, '- SHOWING FIRST LYRIC ANYWAY');
      return 0; // MUDANÇA: Mostrar primeira letra imediatamente ao invés de -1
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

  // SEMPRE renderizar - NUNCA retornar null
  const hasLyrics = lyrics && lyrics.blocks && lyrics.blocks.length > 0;
  
  // Determinar o conteúdo a exibir
  let displayContent;
  
  if (!hasLyrics) {
    console.log('📭 NO LYRICS - showing waiting message');
    displayContent = {
      previous: '',
      current: 'Waiting for music...',
      next: ''
    };
  } else if (lyrics.quality === 'Instrumental' || lyrics.blocks.length === 0) {
    console.log('🎵 INSTRUMENTAL TRACK');
    displayContent = {
      previous: '',
      current: '🎵 Instrumental Track 🎵',
      next: ''
    };
  } else {
    console.log('✅ SHOWING LYRICS - threeLines:', threeLines);
    displayContent = threeLines;
  }

  return (
    <div className="lyrics-display" style={{
      width: '100vw',
      height: '100vh',
      position: 'fixed',
      top: 0,
      left: 0,
      zIndex: 1000,
            display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      pointerEvents: 'none',
      border: 'none',
      padding: 0,
      gap: 0,
      overflow: 'visible',
    }}>
      <div style={{
        color: '#bbb',
        fontSize: 28,
        opacity: 0.44,
        minHeight: 32,
        marginBottom: 0,
        width: '100vw',
        textAlign: 'center',
        textShadow: '2px 2px 8px #000',
        pointerEvents: 'none',
        userSelect: 'none',
        lineHeight: 1.2,
                overflow: 'visible',
      }}>{displayContent.previous || ''}</div>
      <div style={{
        color: '#fff',
        fontSize: 54,
        fontWeight: 700,
        minHeight: 54,
        margin: '10px 0',
        width: '100vw',
        textAlign: 'center',
        textShadow: '4px 4px 16px #000, 0 2px 8px #222',
        letterSpacing: 1,
        lineHeight: 1.22,
        borderRadius: 12,
        pointerEvents: 'none',
        userSelect: 'none',
                overflow: 'visible',
      }}>{displayContent.current || 'SEM LETRA'}</div>
      <div style={{
        color: '#bbb',
        fontSize: 28,
        opacity: 0.44,
        minHeight: 32,
        marginTop: 0,
        width: '100vw',
        textAlign: 'center',
        textShadow: '2px 2px 8px #000',
        pointerEvents: 'none',
        userSelect: 'none',
        lineHeight: 1.2,
                overflow: 'visible',
      }}>{displayContent.next || ''}</div>
    </div>
  );
};
