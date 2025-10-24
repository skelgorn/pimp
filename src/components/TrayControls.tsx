// System tray controls for offset adjustment (simplified for demo)

import { useEffect } from 'react';
import { useAppStore, selectSyncState, selectCurrentTrack } from '../store';

export const TrayControls = () => {
  const syncState = useAppStore(selectSyncState);
  const currentTrack = useAppStore(selectCurrentTrack);

  // Log tray menu state (for demo purposes)
  useEffect(() => {
    const menuState = {
      offset: syncState.global_offset,
      track: currentTrack?.name || 'No track',
      artist: currentTrack?.artist || 'Unknown'
    };
    
    console.log('🎵 Tray Menu State:', menuState);
    
    // TODO: Implement actual tray menu when backend is ready
    // This will be connected to Tauri system tray APIs
  }, [syncState.global_offset, currentTrack]);

  // This component doesn't render anything visible
  return null;
};

export default TrayControls;
