// sync_engine.rs - Core synchronization engine

use crate::types::{TrackInfo, LyricsData, SyncState, OffsetAnchor, TrackOffsetData, Result};
use crate::cache::CacheManager;
use crate::lyrics::LyricsClient;
use crate::config::AppConfig;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{info, warn, debug};
use std::time::{Duration, Instant};
use tauri::{AppHandle, Emitter};

#[derive(Debug)]
pub struct SyncEngine {
    cache: Arc<CacheManager>,
    lyrics_client: Arc<LyricsClient>,
    state: Arc<RwLock<SyncEngineState>>,
    user_lock_until: Arc<RwLock<Option<Instant>>>,
    app_handle: Option<AppHandle>,
}

#[derive(Debug, Clone)]
struct SyncEngineState {
    current_track: Option<TrackInfo>,
    lyrics: Option<LyricsData>,
    current_block_index: i32,
    global_offset: i32,
    is_paused: bool,
    user_has_scrolled: bool,
    last_progress_update: Option<Instant>,
}

impl Default for SyncEngineState {
    fn default() -> Self {
        Self {
            current_track: None,
            lyrics: None,
            current_block_index: -1,
            global_offset: 0,
            is_paused: false,
            user_has_scrolled: false,
            last_progress_update: None,
        }
    }
}

impl SyncEngine {
    pub fn new() -> Self {
        let config = AppConfig::load().unwrap_or_default();
        let cache = Arc::new(CacheManager::new(&config).expect("Failed to create cache manager"));
        let lyrics_client = Arc::new(LyricsClient::new(&config));

        Self {
            cache,
            lyrics_client,
            state: Arc::new(RwLock::new(SyncEngineState::default())),
            user_lock_until: Arc::new(RwLock::new(None)),
            app_handle: None,
        }
    }

    pub fn with_app_handle(mut self, app_handle: AppHandle) -> Self {
        self.app_handle = Some(app_handle);
        self
    }

    fn emit_event<T: serde::Serialize + Clone>(&self, event: &str, payload: T) {
        if let Some(ref app) = self.app_handle {
            info!("🔔 Emitting event: {}", event);
            if let Err(e) = app.emit(event, payload) {
                warn!("❌ Failed to emit event '{}': {}", event, e);
            } else {
                info!("✅ Event '{}' emitted successfully", event);
            }
        } else {
            warn!("❌ No app handle available to emit event '{}'", event);
        }
    }

    pub async fn initialize(&self) -> Result<()> {
        info!("Initializing sync engine...");
        self.cache.init().await?;
        Ok(())
    }

    pub async fn update_track(&self, track: TrackInfo) -> Result<()> {
        let mut state = self.state.write().await;

        // Check if this is a new track
        let is_new_track = state.current_track.as_ref()
            .map(|current| current.id != track.id)
            .unwrap_or(true);

        if is_new_track {
            info!("New track detected: {} - {}", track.artist, track.name);

            // Reset state for new track
            state.current_track = Some(track.clone());
            state.lyrics = None;
            state.current_block_index = -1;
            state.user_has_scrolled = false;
            state.is_paused = !track.is_playing;

            // Load cached offset for this track
            if let Some(offset_data) = self.cache.get_track_offset(&track.artist, &track.name).await {
                state.global_offset = offset_data.global_offset;
                debug!("Loaded cached offset: {}ms", offset_data.global_offset);
            } else {
                state.global_offset = 0;
            }

            // Emit track change event
            self.emit_event("track_changed", &track);

            drop(state); // Release the write lock

            // Fetch lyrics for the new track
            self.fetch_and_cache_lyrics(&track.artist, &track.name).await?;
        } else {
            // Update existing track info (progress, play state, etc.)
            state.current_track = Some(track.clone());
            state.is_paused = !track.is_playing;
            info!("🎮 Updated is_paused: {} (is_playing: {})", state.is_paused, track.is_playing);
        }

        Ok(())
    }

    pub async fn update_progress(&self, progress_ms: u64) -> Result<()> {
        // Check if user lock is active
        {
            let user_lock = self.user_lock_until.read().await;
            if let Some(lock_until) = *user_lock {
                if Instant::now() < lock_until {
                    debug!("Ignoring progress update due to active user lock");
                    return Ok(());
                }
            }
        }

        let mut state = self.state.write().await;

        if let Some(ref lyrics) = state.lyrics {
            if !lyrics.blocks.is_empty() {
                // Apply offset
                let adjusted_progress = (progress_ms as i64 + state.global_offset as i64).max(0) as u64;

                // Find current block
                let new_block_index = self.find_current_block_index(&lyrics.blocks, adjusted_progress);

                if new_block_index != state.current_block_index {
                    debug!("Block changed: {} -> {} (offset: {}ms, progress: {}ms)",
                        state.current_block_index, new_block_index, state.global_offset, progress_ms);
                    state.current_block_index = new_block_index;

                    // Reset scroll state when block changes naturally
                    if !state.user_has_scrolled {
                        // Auto-scroll to current block
                    }
                }
            }
        }

        state.last_progress_update = Some(Instant::now());

        Ok(())
    }

    pub async fn adjust_offset(&mut self, delta: i32) -> Result<i32> {
        info!("Adjusting offset by {}ms", delta);

        let mut state = self.state.write().await;

        if let Some(ref track) = state.current_track {
            let artist = track.artist.clone();
            let name = track.name.clone();
            let new_offset = state.global_offset + delta;
            state.global_offset = new_offset;

            // Set user lock for 5 seconds to prevent automatic updates
            {
                let mut user_lock = self.user_lock_until.write().await;
                *user_lock = Some(Instant::now() + Duration::from_secs(5));
            }

            // Save to cache
            let offset_data = TrackOffsetData {
                anchors: Vec::new(), // TODO: Implement anchor points
                global_offset: new_offset,
                track_id: format!("{}:{}", artist, name),
                last_modified: chrono::Utc::now(),
            };

            self.cache.store_track_offset(&artist, &name, offset_data).await?;

            info!("Offset adjusted to {}ms for {} - {}", new_offset, artist, name);

            // Force immediate recalculation
            if let Some(ref track) = state.current_track {
                if let Some(ref lyrics) = state.lyrics {
                    let adjusted_progress = (track.progress_ms as i64 + new_offset as i64).max(0) as u64;
                    let new_block_index = self.find_current_block_index(&lyrics.blocks, adjusted_progress);
                    state.current_block_index = new_block_index;
                }
            }

            Ok(new_offset)
        } else {
            warn!("No current track for offset adjustment");
            Ok(0)
        }
    }

    pub async fn reset_offset(&mut self) -> Result<i32> {
        info!("Resetting offset to 0");

        let mut state = self.state.write().await;

        if let Some(ref track) = state.current_track {
            let artist = track.artist.clone();
            let name = track.name.clone();
            let progress_ms = track.progress_ms;
            state.global_offset = 0;

            // Clear cached offset
            let offset_data = TrackOffsetData {
                anchors: Vec::new(),
                global_offset: 0,
                track_id: format!("{}:{}", artist, name),
                last_modified: chrono::Utc::now(),
            };

            self.cache.store_track_offset(&artist, &name, offset_data).await?;

            // Force immediate recalculation
            if let Some(ref lyrics) = state.lyrics {
                let new_block_index = self.find_current_block_index(&lyrics.blocks, progress_ms);
                state.current_block_index = new_block_index;
            }

            info!("Offset reset for {} - {}", artist, name);
            Ok(0)
        } else {
            Ok(0)
        }
    }

    pub async fn get_state(&self) -> SyncState {
        let mut state = self.state.write().await;
        info!("🔍 get_state called - is_paused: {}", state.is_paused);

        // Recalcula o bloco atual sempre que get_state é chamado
        if let (Some(ref track), Some(ref lyrics)) = (&state.current_track, &state.lyrics) {
            let adjusted_progress = (track.progress_ms as i64 + state.global_offset as i64).max(0) as u64;
            let new_block_index = self.find_current_block_index(&lyrics.blocks, adjusted_progress);
            state.current_block_index = new_block_index;
        }

        SyncState {
            current_track: state.current_track.clone(),
            lyrics: state.lyrics.clone(),
            current_block_index: state.current_block_index,
            global_offset: state.global_offset,
            is_paused: state.is_paused,
            user_has_scrolled: state.user_has_scrolled,
        }
    }

    pub async fn fetch_lyrics(&mut self, artist: &str, title: &str) -> Result<Option<LyricsData>> {
        // Check cache first
        if let Some(cached_lyrics) = self.cache.get_lyrics(artist, title).await {
            info!("Lyrics found in cache for {} - {}", artist, title);

            // Update state with cached lyrics
            {
                let mut state = self.state.write().await;
                state.lyrics = Some(cached_lyrics.clone());
                state.current_block_index = -1;
            }

            return Ok(Some(cached_lyrics));
        }

        // Fetch from LRCLIB
        match self.lyrics_client.search_lyrics(artist, title).await {
            Ok(Some(lyrics)) => {
                info!("Lyrics fetched from LRCLIB for {} - {} ({})", artist, title, lyrics.source);

                // Cache the lyrics
                if let Err(e) = self.cache.store_lyrics(artist, title, lyrics.clone()).await {
                    warn!("Failed to cache lyrics: {}", e);
                }

                // Update state
                {
                    let mut state = self.state.write().await;
                    state.lyrics = Some(lyrics.clone());
                    state.current_block_index = -1;
                }

                Ok(Some(lyrics))
            }
            Ok(None) => {
                warn!("No lyrics found for {} - {}", artist, title);
                Ok(None)
            }
            Err(e) => {
                warn!("Error fetching lyrics for {} - {}: {}", artist, title, e);
                Err(e)
            }
        }
    }

    async fn fetch_and_cache_lyrics(&self, artist: &str, title: &str) -> Result<()> {
        // This is a non-mutable version for internal use
        // Check cache first
        if let Some(cached_lyrics) = self.cache.get_lyrics(artist, title).await {
            info!("Lyrics found in cache for {} - {}", artist, title);

            let mut state = self.state.write().await;
            state.lyrics = Some(cached_lyrics.clone());
            state.current_block_index = -1;
            drop(state);

            // Emit lyrics found event for cached lyrics too!
            self.emit_event("lyrics_found", &cached_lyrics);

            return Ok(());
        }

        // Fetch from LRCLIB
        match self.lyrics_client.search_lyrics(artist, title).await {
            Ok(Some(lyrics)) => {
                info!("Lyrics fetched from LRCLIB for {} - {} ({})", artist, title, lyrics.source);

                // Cache the lyrics
                if let Err(e) = self.cache.store_lyrics(artist, title, lyrics.clone()).await {
                    warn!("Failed to cache lyrics: {}", e);
                }

                // Update state and emit event
                let mut state = self.state.write().await;
                state.lyrics = Some(lyrics.clone());
                state.current_block_index = -1;
                drop(state);

                // Emit lyrics found event
                self.emit_event("lyrics_found", &lyrics);

                Ok(())
            }
            Ok(None) => {
                warn!("No lyrics found for {} - {}", artist, title);
                Ok(())
            }
            Err(e) => {
                warn!("Error fetching lyrics for {} - {}: {}", artist, title, e);
                Err(e)
            }
        }
    }

    fn find_current_block_index(&self, blocks: &[crate::types::LyricsBlock], progress_ms: u64) -> i32 {
        if blocks.is_empty() {
            return -1;
        }

        // If before first block, show first block
        if progress_ms < blocks[0].start {
            return 0;
        }

        // Find the current block
        for (i, block) in blocks.iter().enumerate() {
            if progress_ms >= block.start && progress_ms < block.end {
                return i as i32;
            }
        }

        // If after all blocks, show last block
        (blocks.len() - 1) as i32
    }

    pub async fn set_user_scrolled(&self, scrolled: bool) {
        let mut state = self.state.write().await;
        state.user_has_scrolled = scrolled;
    }

    // Public access to cache for clearing operations
    pub fn get_cache(&self) -> &Arc<CacheManager> {
        &self.cache
    }
}