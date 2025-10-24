// Track information and playback controls component

import React from 'react';
import { motion } from 'framer-motion';
import { Play, Pause, SkipBack, SkipForward, Music } from 'lucide-react';
import { useAppStore, selectCurrentTrack, selectSyncState, selectProgress } from '../store';
import { useTauriCommands } from '../hooks/useTauri';
import { clsx } from 'clsx';

interface TrackInfoProps {
  className?: string;
  compact?: boolean;
}

export const TrackInfo: React.FC<TrackInfoProps> = ({ className, compact = false }) => {
  const currentTrack = useAppStore(selectCurrentTrack);
  const syncState = useAppStore(selectSyncState);
  const progress = useAppStore(selectProgress);
  const { adjustOffset, resetOffset } = useTauriCommands();

  // Format time in mm:ss
  const formatTime = (ms: number) => {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  // Progress percentage
  const progressPercent = currentTrack
    ? (progress / currentTrack.duration_ms) * 100
    : 0;

  if (!currentTrack) {
    return (
      <div className={clsx('track-info', className)}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-center p-4"
        >
          <Music className="w-6 h-6 text-white/40 mr-2" />
          <span className="text-white/60">No track playing</span>
        </motion.div>
      </div>
    );
  }

  if (compact) {
    return (
      <motion.div
        layout
        className={clsx('track-info-compact', className)}
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
      >
        <div className="flex items-center space-x-2">
          <AlbumArt image={currentTrack.album.images[0]?.url} size="sm" />
          <div className="flex-1 min-w-0">
            <p className="text-white text-sm font-medium truncate">
              {currentTrack.name}
            </p>
            <p className="text-white/60 text-xs truncate">
              {currentTrack.artist}
            </p>
          </div>
          <PlaybackIndicator isPlaying={currentTrack.is_playing} />
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      layout
      className={clsx('track-info', className)}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
    >
      {/* Album Art and Track Info */}
      <div className="flex items-center space-x-4 mb-4">
        <AlbumArt image={currentTrack.album.images[0]?.url} size="lg" />

        <div className="flex-1 min-w-0">
          <h2 className="text-white text-lg font-semibold truncate mb-1">
            {currentTrack.name}
          </h2>
          <p className="text-white/80 text-sm truncate mb-1">
            {currentTrack.artist}
          </p>
          <p className="text-white/60 text-xs truncate">
            {currentTrack.album.name}
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <PlaybackIndicator isPlaying={currentTrack.is_playing} />
          {syncState.global_offset !== 0 && (
            <OffsetBadge offset={syncState.global_offset} />
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between text-xs text-white/60 mb-1">
          <span>{formatTime(progress)}</span>
          <span>{formatTime(currentTrack.duration_ms)}</span>
        </div>
        <div className="w-full bg-white/20 rounded-full h-1">
          <motion.div
            className="bg-white rounded-full h-1"
            initial={{ width: 0 }}
            animate={{ width: `${progressPercent}%` }}
            transition={{ ease: "linear", duration: 0.1 }}
          />
        </div>
      </div>

      {/* Controls */}
      <div className="flex justify-center space-x-4">
        <ControlButton
          icon={SkipBack}
          onClick={() => adjustOffset(-500)}
          tooltip="Offset -500ms"
        />
        <ControlButton
          icon={currentTrack.is_playing ? Pause : Play}
          onClick={() => {}}
          tooltip={currentTrack.is_playing ? "Pause" : "Play"}
          disabled
        />
        <ControlButton
          icon={SkipForward}
          onClick={() => adjustOffset(500)}
          tooltip="Offset +500ms"
        />
      </div>

      {/* Reset button for offset */}
      {syncState.global_offset !== 0 && (
        <motion.button
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={resetOffset}
          className="mt-3 text-xs text-white/60 hover:text-white transition-colors"
        >
          Reset Offset
        </motion.button>
      )}
    </motion.div>
  );
};

interface AlbumArtProps {
  image?: string;
  size: 'sm' | 'lg';
}

const AlbumArt: React.FC<AlbumArtProps> = ({ image, size }) => {
  const sizeClasses = {
    sm: 'w-8 h-8',
    lg: 'w-16 h-16',
  };

  return (
    <div
      className={clsx(
        'rounded-lg overflow-hidden flex-shrink-0 bg-white/10',
        sizeClasses[size]
      )}
    >
      {image ? (
        <img
          src={image}
          alt="Album art"
          className="w-full h-full object-cover"
          loading="lazy"
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center">
          <Music className={clsx(
            'text-white/40',
            size === 'sm' ? 'w-4 h-4' : 'w-8 h-8'
          )} />
        </div>
      )}
    </div>
  );
};

interface PlaybackIndicatorProps {
  isPlaying: boolean;
}

const PlaybackIndicator: React.FC<PlaybackIndicatorProps> = ({ isPlaying }) => {
  return (
    <motion.div
      animate={{
        scale: isPlaying ? [1, 1.1, 1] : 1,
        opacity: isPlaying ? 1 : 0.5,
      }}
      transition={{
        scale: { repeat: Infinity, duration: 1.5 },
        opacity: { duration: 0.3 },
      }}
      className="flex items-center justify-center"
    >
      {isPlaying ? (
        <Play className="w-4 h-4 text-green-400 fill-current" />
      ) : (
        <Pause className="w-4 h-4 text-white/60" />
      )}
    </motion.div>
  );
};

interface OffsetBadgeProps {
  offset: number;
}

const OffsetBadge: React.FC<OffsetBadgeProps> = ({ offset }) => {
  return (
    <motion.div
      initial={{ scale: 0 }}
      animate={{ scale: 1 }}
      className={clsx(
        'px-2 py-1 rounded-full text-xs font-mono',
        offset > 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
      )}
    >
      {offset > 0 ? '+' : ''}{offset}ms
    </motion.div>
  );
};

interface ControlButtonProps {
  icon: React.ComponentType<any>;
  onClick: () => void;
  tooltip: string;
  disabled?: boolean;
}

const ControlButton: React.FC<ControlButtonProps> = ({
  icon: Icon,
  onClick,
  tooltip,
  disabled = false,
}) => {
  return (
    <motion.button
      whileHover={{ scale: disabled ? 1 : 1.1 }}
      whileTap={{ scale: disabled ? 1 : 0.9 }}
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        'p-2 rounded-full transition-colors',
        disabled
          ? 'text-white/30 cursor-not-allowed'
          : 'text-white/70 hover:text-white hover:bg-white/10'
      )}
      title={tooltip}
    >
      <Icon className="w-5 h-5" />
    </motion.button>
  );
};