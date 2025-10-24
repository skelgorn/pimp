// offset_manager.rs - Advanced offset management with anchor points and caching

use std::collections::HashMap;
use std::path::PathBuf;
use chrono::Utc;
use tokio::sync::RwLock;
use tracing::{info, warn, error};

use crate::types::{Result, AppError, OffsetAnchor, TrackOffsetData, OffsetCache};

pub struct OffsetManager {
    cache: RwLock<OffsetCache>,
    cache_file: PathBuf,
}

impl OffsetManager {
    pub fn new(cache_dir: PathBuf) -> Self {
        let cache_file = cache_dir.join("offset_cache.json");
        
        Self {
            cache: RwLock::new(OffsetCache {
                tracks: HashMap::new(),
                version: 1,
            }),
            cache_file,
        }
    }

    /// Initialize and load existing cache
    pub async fn initialize(&self) -> Result<()> {
        info!("🎯 Initializing OffsetManager...");
        
        if self.cache_file.exists() {
            match self.load_cache().await {
                Ok(_) => info!("✅ Offset cache loaded successfully"),
                Err(e) => {
                    warn!("⚠️ Failed to load offset cache: {:?}", e);
                    info!("🔄 Starting with empty cache");
                }
            }
        } else {
            info!("📝 Creating new offset cache");
        }
        
        Ok(())
    }

    /// Load cache from disk
    async fn load_cache(&self) -> Result<()> {
        let content = tokio::fs::read_to_string(&self.cache_file).await?;
        let loaded_cache: OffsetCache = serde_json::from_str(&content)?;
        
        let mut cache = self.cache.write().await;
        *cache = loaded_cache;
        
        info!("📂 Loaded {} track offsets from cache", cache.tracks.len());
        Ok(())
    }

    /// Save cache to disk
    async fn save_cache(&self) -> Result<()> {
        let cache = self.cache.read().await;
        let content = serde_json::to_string_pretty(&*cache)?;
        
        // Ensure directory exists
        if let Some(parent) = self.cache_file.parent() {
            tokio::fs::create_dir_all(parent).await?;
        }
        
        tokio::fs::write(&self.cache_file, content).await?;
        info!("💾 Offset cache saved with {} tracks", cache.tracks.len());
        Ok(())
    }

    /// Get offset for a specific timestamp using anchor points
    pub async fn get_offset_for_timestamp(&self, track_id: &str, timestamp: u64) -> i32 {
        let cache = self.cache.read().await;
        
        if let Some(track_data) = cache.tracks.get(track_id) {
            // Find the most recent anchor point before or at this timestamp
            let mut best_anchor: Option<&OffsetAnchor> = None;
            
            for anchor in &track_data.anchors {
                if anchor.timestamp <= timestamp {
                    if best_anchor.is_none() || anchor.timestamp > best_anchor.unwrap().timestamp {
                        best_anchor = Some(anchor);
                    }
                }
            }
            
            if let Some(anchor) = best_anchor {
                info!("🎯 Using anchor point at {}ms with offset {}ms", anchor.timestamp, anchor.offset);
                return anchor.offset;
            }
            
            // Fallback to global offset
            info!("🌐 Using global offset: {}ms", track_data.global_offset);
            return track_data.global_offset;
        }
        
        // No data for this track
        info!("❓ No offset data for track {}, using 0", track_id);
        0
    }

    /// Set global offset for a track
    pub async fn set_global_offset(&self, track_id: &str, offset: i32) -> Result<()> {
        info!("🎯 Setting global offset for track {}: {}ms", track_id, offset);
        
        let mut cache = self.cache.write().await;
        
        let track_data = cache.tracks.entry(track_id.to_string()).or_insert_with(|| {
            TrackOffsetData {
                anchors: Vec::new(),
                global_offset: 0,
                track_id: track_id.to_string(),
                last_modified: Utc::now(),
            }
        });
        
        track_data.global_offset = offset;
        track_data.last_modified = Utc::now();
        
        drop(cache); // Release lock before saving
        self.save_cache().await?;
        
        Ok(())
    }

    /// Add or update an anchor point for specific timestamp
    pub async fn set_anchor_offset(&self, track_id: &str, timestamp: u64, offset: i32) -> Result<()> {
        info!("⚓ Setting anchor offset for track {} at {}ms: {}ms", track_id, timestamp, offset);
        
        let mut cache = self.cache.write().await;
        
        let track_data = cache.tracks.entry(track_id.to_string()).or_insert_with(|| {
            TrackOffsetData {
                anchors: Vec::new(),
                global_offset: 0,
                track_id: track_id.to_string(),
                last_modified: Utc::now(),
            }
        });
        
        // Remove existing anchor at this timestamp if it exists
        track_data.anchors.retain(|anchor| anchor.timestamp != timestamp);
        
        // Add new anchor
        track_data.anchors.push(OffsetAnchor { timestamp, offset });
        
        // Sort anchors by timestamp
        track_data.anchors.sort_by_key(|anchor| anchor.timestamp);
        
        track_data.last_modified = Utc::now();
        
        info!("📍 Track {} now has {} anchor points", track_id, track_data.anchors.len());
        
        drop(cache); // Release lock before saving
        self.save_cache().await?;
        
        Ok(())
    }

    /// Remove an anchor point
    pub async fn remove_anchor(&self, track_id: &str, timestamp: u64) -> Result<()> {
        info!("🗑️ Removing anchor for track {} at {}ms", track_id, timestamp);
        
        let mut cache = self.cache.write().await;
        
        if let Some(track_data) = cache.tracks.get_mut(track_id) {
            let initial_count = track_data.anchors.len();
            track_data.anchors.retain(|anchor| anchor.timestamp != timestamp);
            
            if track_data.anchors.len() < initial_count {
                track_data.last_modified = Utc::now();
                info!("✅ Anchor removed. Track {} now has {} anchor points", track_id, track_data.anchors.len());
                
                drop(cache);
                self.save_cache().await?;
            } else {
                info!("❓ No anchor found at timestamp {}ms", timestamp);
            }
        }
        
        Ok(())
    }

    /// Reset all offsets for a track
    pub async fn reset_track_offsets(&self, track_id: &str) -> Result<()> {
        info!("🔄 Resetting all offsets for track {}", track_id);
        
        let mut cache = self.cache.write().await;
        cache.tracks.remove(track_id);
        
        drop(cache);
        self.save_cache().await?;
        
        info!("✅ All offsets reset for track {}", track_id);
        Ok(())
    }

    /// Get all anchor points for a track (for UI display)
    pub async fn get_track_anchors(&self, track_id: &str) -> Vec<OffsetAnchor> {
        let cache = self.cache.read().await;
        
        if let Some(track_data) = cache.tracks.get(track_id) {
            track_data.anchors.clone()
        } else {
            Vec::new()
        }
    }

    /// Get global offset for a track
    pub async fn get_global_offset(&self, track_id: &str) -> i32 {
        let cache = self.cache.read().await;
        
        if let Some(track_data) = cache.tracks.get(track_id) {
            track_data.global_offset
        } else {
            0
        }
    }

    /// Clear all cached offsets
    pub async fn clear_all_offsets(&self) -> Result<()> {
        info!("🗑️ Clearing all offset data");
        
        let mut cache = self.cache.write().await;
        cache.tracks.clear();
        
        drop(cache);
        self.save_cache().await?;
        
        info!("✅ All offset data cleared");
        Ok(())
    }
}
