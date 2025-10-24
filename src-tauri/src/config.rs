// config.rs - Configuration management for LetrasPIP

use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use anyhow::Result;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub spotify: SpotifyConfig,
    pub lyrics: LyricsConfig,
    pub ui: UiConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpotifyConfig {
    pub client_id: String,
    pub client_secret: String,
    pub redirect_uri: String,
    pub polling_interval_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LyricsConfig {
    pub lrclib_base_url: String,
    pub cache_duration_hours: u64,
    pub fallback_sources: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UiConfig {
    pub font_family: String,
    pub font_size: u32,
    pub theme: String,
    pub window_position: Option<(i32, i32)>,
    pub window_size: Option<(u32, u32)>,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            spotify: SpotifyConfig {
                client_id: std::env::var("VITE_SPOTIFY_CLIENT_ID")
                    .or_else(|_| std::env::var("SPOTIFY_CLIENT_ID"))
                    .unwrap_or_else(|_| "your_client_id".to_string()),
                client_secret: std::env::var("VITE_SPOTIFY_CLIENT_SECRET")
                    .or_else(|_| std::env::var("SPOTIFY_CLIENT_SECRET"))
                    .unwrap_or_else(|_| "your_client_secret".to_string()),
                redirect_uri: std::env::var("VITE_SPOTIFY_REDIRECT_URI")
                    .unwrap_or_else(|_| "http://localhost:8080/callback".to_string()),
                polling_interval_ms: 100,
            },
            lyrics: LyricsConfig {
                lrclib_base_url: "https://lrclib.net/api".to_string(),
                cache_duration_hours: 24,
                fallback_sources: vec!["lrclib".to_string()],
            },
            ui: UiConfig {
                font_family: "Segoe UI".to_string(),
                font_size: 16,
                theme: "dark".to_string(),
                window_position: None,
                window_size: Some((800, 600)),
            },
        }
    }
}

impl AppConfig {
    pub fn load() -> Result<Self> {
        let config_path = Self::config_path()?;

        if config_path.exists() {
            let content = std::fs::read_to_string(&config_path)?;
            let config: AppConfig = serde_json::from_str(&content)?;
            Ok(config)
        } else {
            let config = AppConfig::default();
            config.save()?;
            Ok(config)
        }
    }

    pub fn save(&self) -> Result<()> {
        let config_path = Self::config_path()?;

        if let Some(parent) = config_path.parent() {
            std::fs::create_dir_all(parent)?;
        }

        let content = serde_json::to_string_pretty(self)?;
        std::fs::write(&config_path, content)?;

        Ok(())
    }

    pub fn config_path() -> Result<PathBuf> {
        let config_dir = dirs::config_dir()
            .ok_or_else(|| anyhow::anyhow!("Could not find config directory"))?;

        Ok(config_dir.join("letraspip").join("config.json"))
    }

    pub fn cache_dir() -> Result<PathBuf> {
        let cache_dir = dirs::cache_dir()
            .ok_or_else(|| anyhow::anyhow!("Could not find cache directory"))?;

        Ok(cache_dir.join("letraspip"))
    }

    pub fn data_dir() -> Result<PathBuf> {
        let data_dir = dirs::data_dir()
            .ok_or_else(|| anyhow::anyhow!("Could not find data directory"))?;

        Ok(data_dir.join("letraspip"))
    }
}