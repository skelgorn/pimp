// Ultra minimalist app - just floating lyrics + tray controls

import { useEffect } from 'react';
import { LyricsDisplay } from './components/LyricsDisplay';
import { TrayControls } from './components/TrayControls';
import { useTauriEvents, useKeyboardShortcuts } from './hooks/useTauri';
import { useAppStore, selectError } from './store';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle } from 'lucide-react';
import './App.css';

function App() {
  const error = useAppStore(selectError);

  // Set up event listeners and keyboard shortcuts
  useTauriEvents();
  useKeyboardShortcuts();

  // Clear error after 3 seconds
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        useAppStore.getState().setError(null);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  // Drag handled by data-tauri-drag-region on main container

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        background: 'transparent',
        position: 'relative',
        pointerEvents: 'none', // CRÍTICO: Toda a área é não-clicável por padrão
        overflow: 'hidden'
      }}
    >

      {/* Error notification (minimal) */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            style={{
              position: 'fixed',
              top: '20px',
              right: '20px',
              zIndex: 10001,
              pointerEvents: 'auto'
            }}
          >
            <div style={{
              background: 'rgba(239, 68, 68, 0.9)',
              backdropFilter: 'blur(8px)',
              color: 'white',
              padding: '8px 12px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '12px',
              maxWidth: '200px'
            }}>
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>


      {/* Main floating lyrics */}
      <LyricsDisplay />

      {/* Tray controls (invisible component) */}
      <TrayControls />
    </div>
  );
}

export default App;
