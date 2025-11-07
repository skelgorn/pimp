// Ultra minimalist app - just floating lyrics + tray controls

import { useEffect } from 'react';
import { LyricsDisplay } from './components/LyricsDisplay';
import { useTauriEvents, useKeyboardShortcuts } from './hooks/useTauri';
import { useAppStore, selectError } from './store';
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
    <div className="app-container">
      <LyricsDisplay />
    </div>
  );
}

export default App;
