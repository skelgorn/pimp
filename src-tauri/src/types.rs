// types.rs - Core data types for LetrasPIP

use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrackInfo {
    pub id: String,
    pub name: String,
    pub artist: String,
    pub album: AlbumInfo,
    pub duration_ms: u64,
    pub is_playing: bool,
    pub progress_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlbumInfo {
    pub name: String,
    pub images: Vec<ImageInfo>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImageInfo {
    pub url: String,
    pub width: Option<u32>,
    pub height: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LyricsBlock {
    pub start: u64,
    pub end: u64,
    pub text: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LyricsData {
    pub blocks: Vec<LyricsBlock>,
    pub source: String,
    pub quality: LyricsQuality,
    pub confidence: f32,
    pub cached_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LyricsQuality {
    High,
    Medium,
    Low,
    Instrumental,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncState {
    pub current_track: Option<TrackInfo>,
    pub lyrics: Option<LyricsData>,
    pub current_block_index: i32,
    pub global_offset: i32,
    pub is_paused: bool,
    pub user_has_scrolled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OffsetAnchor {
    pub timestamp: u64,
    pub offset: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrackOffsetData {
    pub anchors: Vec<OffsetAnchor>,
    pub global_offset: i32,
    pub track_id: String,
    pub last_modified: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OffsetCache {
    pub tracks: std::collections::HashMap<String, TrackOffsetData>,
    pub version: u32,
}

// Error types
#[derive(Debug, thiserror::Error, serde::Serialize)]
pub enum AppError {
    #[error("Spotify API error: {0}")]
    Spotify(String),

    #[error("Lyrics not found")]
    LyricsNotFound,

    #[error("Cache error: {0}")]
    Cache(String),

    #[error("Configuration error: {0}")]
    Config(String),

    #[error("IO error: {0}")]
    Io(String),

    #[error("JSON error: {0}")]
    Json(String),

    #[error("Anyhow error: {0}")]
    Anyhow(String),
}

impl From<reqwest::Error> for AppError {
    fn from(err: reqwest::Error) -> Self {
        AppError::Spotify(err.to_string())
    }
}

impl From<std::io::Error> for AppError {
    fn from(err: std::io::Error) -> Self {
        AppError::Io(err.to_string())
    }
}

impl From<serde_json::Error> for AppError {
    fn from(err: serde_json::Error) -> Self {
        AppError::Json(err.to_string())
    }
}

impl From<anyhow::Error> for AppError {
    fn from(err: anyhow::Error) -> Self {
        AppError::Anyhow(err.to_string())
    }
}

pub type Result<T> = std::result::Result<T, AppError>;