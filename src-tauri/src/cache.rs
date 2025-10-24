// cache.rs - Cache management for lyrics and offset data

use crate::types::{LyricsData, TrackOffsetData, Result, AppError};
use crate::config::AppConfig;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;
use chrono::{DateTime, Utc, Duration};
use lru::LruCache;
use std::num::NonZeroUsize;
use tokio::sync::RwLock;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct CachedLyrics {
    data: LyricsData,
    expires_at: DateTime<Utc>,
}

#[derive(Debug)]
pub struct CacheManager {
    memory_cache: RwLock<LruCache<String, CachedLyrics>>,
    offset_cache: RwLock<HashMap<String, TrackOffsetData>>,
    cache_dir: PathBuf,
    cache_duration: Duration,
}

impl CacheManager {
    pub fn new(config: &AppConfig) -> Result<Self> {
        let cache_dir = AppConfig::cache_dir()?;
        std::fs::create_dir_all(&cache_dir)?;

        let cache_duration = Duration::hours(config.lyrics.cache_duration_hours as i64);

        // Memory cache for 50 recent lyrics
        let memory_cache = LruCache::new(NonZeroUsize::new(50).unwrap());

        Ok(Self {
            memory_cache: RwLock::new(memory_cache),
            offset_cache: RwLock::new(HashMap::new()),
            cache_dir,
            cache_duration,
        })
    }

    pub async fn init(&self) -> Result<()> {
        // Load offset cache from disk
        self.load_offset_cache().await?;
        Ok(())
    }

    // Lyrics cache methods
    pub async fn get_lyrics(&self, artist: &str, title: &str) -> Option<LyricsData> {
        let key = self.lyrics_cache_key(artist, title);

        // Check memory cache first
        {
            let mut cache = self.memory_cache.write().await;
            if let Some(cached) = cache.get(&key) {
                if cached.expires_at > Utc::now() {
                    return Some(cached.data.clone());
                } else {
                    // Remove expired entry
                    cache.pop(&key);
                }
            }
        }

        // Check disk cache
        if let Ok(cached) = self.load_lyrics_from_disk(&key).await {
            if cached.expires_at > Utc::now() {
                // Add back to memory cache
                let mut cache = self.memory_cache.write().await;
                cache.put(key, cached.clone());
                return Some(cached.data);
            }
        }

        None
    }

    pub async fn store_lyrics(&self, artist: &str, title: &str, lyrics: LyricsData) -> Result<()> {
        let key = self.lyrics_cache_key(artist, title);
        let expires_at = Utc::now() + self.cache_duration;

        let cached = CachedLyrics {
            data: lyrics,
            expires_at,
        };

        // Store in memory cache
        {
            let mut cache = self.memory_cache.write().await;
            cache.put(key.clone(), cached.clone());
        }

        // Store on disk
        self.save_lyrics_to_disk(&key, &cached).await?;

        Ok(())
    }

    // Offset cache methods
    pub async fn get_track_offset(&self, artist: &str, title: &str) -> Option<TrackOffsetData> {
        let key = self.track_key(artist, title);
        let cache = self.offset_cache.read().await;
        cache.get(&key).cloned()
    }

    pub async fn store_track_offset(&self, artist: &str, title: &str, offset_data: TrackOffsetData) -> Result<()> {
        let key = self.track_key(artist, title);

        {
            let mut cache = self.offset_cache.write().await;
            cache.insert(key, offset_data);
        }

        // Save to disk
        self.save_offset_cache().await?;

        Ok(())
    }
    pub async fn update_global_offset(&self, artist: &str, title: &str, offset: i32) -> Result<()> {
        let key = self.track_key(artist, title);

        {
            let mut cache = self.offset_cache.write().await;
            let entry = cache.entry(key.clone()).or_insert_with(|| TrackOffsetData {
                anchors: Vec::new(),
                global_offset: 0,
                track_id: key.clone(),
                last_modified: chrono::Utc::now(),
            });
            entry.global_offset = offset;
            entry.last_modified = chrono::Utc::now();
        }

        self.save_offset_cache().await?;
        Ok(())
    }

    // Private helper methods
    fn lyrics_cache_key(&self, artist: &str, title: &str) -> String {
        format!("{}_{}",
            artist.to_lowercase().replace(' ', "_"),
            title.to_lowercase().replace(' ', "_")
        )
    }

    fn track_key(&self, artist: &str, title: &str) -> String {
        format!("{} - {}", artist, title)
    }

    async fn load_lyrics_from_disk(&self, key: &str) -> Result<CachedLyrics> {
        let file_path = self.cache_dir.join(format!("{}.json", key));
        let content = tokio::fs::read_to_string(file_path).await?;
        let cached: CachedLyrics = serde_json::from_str(&content)?;
        Ok(cached)
    }

    async fn save_lyrics_to_disk(&self, key: &str, cached: &CachedLyrics) -> Result<()> {
        let file_path = self.cache_dir.join(format!("{}.json", key));
        let content = serde_json::to_string_pretty(cached)?;
        tokio::fs::write(file_path, content).await?;
        Ok(())
    }

    async fn load_offset_cache(&self) -> Result<()> {
        let file_path = self.cache_dir.join("offsets.json");

        if file_path.exists() {
            let content = tokio::fs::read_to_string(file_path).await?;
            let cache_data: HashMap<String, TrackOffsetData> = serde_json::from_str(&content)?;

            let mut cache = self.offset_cache.write().await;
            *cache = cache_data;
        }

        Ok(())
    }

    async fn save_offset_cache(&self) -> Result<()> {
        let file_path = self.cache_dir.join("offsets.json");

        let cache = self.offset_cache.read().await;
        let content = serde_json::to_string_pretty(&*cache)?;
        drop(cache);

        tokio::fs::write(file_path, content).await?;
        Ok(())
    }

    pub async fn clear_lyrics_cache(&self) -> Result<()> {
        // Clear memory cache
        {
            let mut cache = self.memory_cache.write().await;
            cache.clear();
        }

        // Clear disk cache
        let cache_dir = &self.cache_dir;
        if cache_dir.exists() {
            let mut entries = tokio::fs::read_dir(cache_dir).await?;
            while let Some(entry) = entries.next_entry().await? {
                let path = entry.path();
                if path.extension().and_then(|s| s.to_str()) == Some("json")
                    && path.file_stem().and_then(|s| s.to_str()) != Some("offsets") {
                    tokio::fs::remove_file(path).await?;
                }
            }
        }

        Ok(())
    }
}