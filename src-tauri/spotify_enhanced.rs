// spotify.rs - Enhanced Spotify Web API integration with advanced troubleshooting

use crate::types::{TrackInfo, AlbumInfo, ImageInfo, Result, AppError};
use crate::config::AppConfig;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tokio::time::{sleep, Duration};
use tracing::{info, warn, error, debug};
use base64::Engine;
use url::Url;
use warp::Filter;
use tokio::sync::oneshot;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct SpotifyToken {
    access_token: String,
    token_type: String,
    expires_in: u64,
    refresh_token: Option<String>,
    scope: Option<String>,
    #[serde(skip)]
    obtained_at: Option<std::time::Instant>,
}

impl SpotifyToken {
    fn is_expired(&self) -> bool {
        if let Some(obtained_at) = self.obtained_at {
            let elapsed = obtained_at.elapsed().as_secs();
            // Refresh 5 minutes before actual expiration
            elapsed >= (self.expires_in.saturating_sub(300))
        } else {
            true
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct SpotifyCurrentlyPlaying {
    item: Option<SpotifyTrack>,
    is_playing: bool,
    progress_ms: Option<u64>,
    context: Option<SpotifyContext>,
    currently_playing_type: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct SpotifyTrack {
    id: String,
    name: String,
    artists: Vec<SpotifyArtist>,
    album: SpotifyAlbum,
    duration_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct SpotifyArtist {
    name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct SpotifyAlbum {
    name: String,
    images: Vec<SpotifyImage>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct SpotifyImage {
    url: String,
    width: Option<u32>,
    height: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct SpotifyContext {
    #[serde(rename = "type")]
    context_type: String,
    uri: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct SpotifyDevice {
    id: String,
    is_active: bool,
    name: String,
    #[serde(rename = "type")]
    device_type: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct SpotifyDevicesResponse {
    devices: Vec<SpotifyDevice>,
}

#[derive(Debug)]
pub struct SpotifyClient {
    client: Client,
    config: AppConfig,
    token: Option<SpotifyToken>,
    last_token_refresh: Option<std::time::Instant>,
    user_country: Option<String>,
}

impl SpotifyClient {
    pub fn new() -> Self {
        let config = AppConfig::load().unwrap_or_default();

        Self {
            client: Client::new(),
            config,
            token: None,
            last_token_refresh: None,
            user_country: None,
        }
    }

    pub async fn initialize(&mut self) -> Result<()> {
        info!("🚀 Initializing Enhanced Spotify client...");

        // Try to load existing token
        if let Ok(mut token) = self.load_token().await {
            token.obtained_at = Some(std::time::Instant::now());
            self.token = Some(token);
            info!("✅ Loaded existing Spotify token");

            // Validate token and get user country
            match self.get_current_user().await {
                Ok(user_data) => {
                    if let Some(country) = user_data.get("country").and_then(|c| c.as_str()) {
                        self.user_country = Some(country.to_string());
                        info!("🌍 User country detected: {}", country);
                    }
                }
                Err(_) => {
                    warn!("⚠️ Existing token invalid, will need to re-authenticate");
                    self.token = None;
                }
            }
        }

        // If no valid token, initiate OAuth flow
        if self.token.is_none() {
            self.authenticate().await?;
        }

        Ok(())
    }

    async fn ensure_valid_token(&mut self) -> Result<()> {
        if let Some(token) = &self.token {
            if token.is_expired() {
                warn!("🔄 Token expired, refreshing proactively...");
                self.refresh_token().await?;
            }
        } else {
            return Err(AppError::Config("No token available".to_string()));
        }
        Ok(())
    }

    pub async fn get_current_track(&mut self) -> Result<Option<TrackInfo>> {
        debug!("🎵 get_current_track called");
        
        // Ensure token is valid before making requests
        self.ensure_valid_token().await?;

        // Strategy 1: Try currently-playing with enhanced parameters
        if let Ok(Some(track)) = self.try_currently_playing_enhanced().await {
            return Ok(Some(track));
        }

        // Strategy 2: Try player endpoint with market parameter
        if let Ok(Some(track)) = self.try_player_endpoint().await {
            return Ok(Some(track));
        }

        // Strategy 3: Try recently played as fallback
        if let Ok(Some(track)) = self.try_recently_played().await {
            return Ok(Some(track));
        }

        // Strategy 4: Check if devices are available
        self.check_devices_status().await;

        Ok(None)
    }

    async fn try_currently_playing_enhanced(&mut self) -> Result<Option<TrackInfo>> {
        let token = self.token.as_ref().ok_or_else(|| AppError::Config("No token".to_string()))?;
        
        // Enhanced URL with all recommended parameters
        let market = self.user_country.as_deref().unwrap_or("from_token");
        let url = format!(
            "https://api.spotify.com/v1/me/player/currently-playing?market={}&additional_types=track,episode",
            market
        );

        info!("🎯 Strategy 1: Enhanced currently-playing endpoint");
        info!("📍 URL: {}", url);

        let response = self.client
            .get(&url)
            .header("Authorization", format!("Bearer {}", token.access_token))
            .header("Accept", "application/json")
            .header("Content-Type", "application/json")
            .header("Accept-Language", "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7")
            .send()
            .await?;

        info!("📊 Response status: {}", response.status());

        match response.status().as_u16() {
            200 => {
                let currently_playing: SpotifyCurrentlyPlaying = response.json().await?;
                if let Some(track) = currently_playing.item {
                    info!("✅ Strategy 1 SUCCESS: Found track via currently-playing");
                    return Ok(Some(self.convert_track_info(track, currently_playing)?));
                }
            }
            204 => {
                info!("⚠️ Strategy 1: 204 No Content - trying next strategy");
            }
            401 => {
                warn!("🔑 Strategy 1: 401 Unauthorized - refreshing token");
                self.refresh_token().await?;
                return self.try_currently_playing_enhanced().await;
            }
            _ => {
                let error_text = response.text().await.unwrap_or_default();
                warn!("❌ Strategy 1 failed: {} - {}", response.status(), error_text);
            }
        }

        Ok(None)
    }

    async fn try_player_endpoint(&mut self) -> Result<Option<TrackInfo>> {
        let token = self.token.as_ref().ok_or_else(|| AppError::Config("No token".to_string()))?;
        
        let market = self.user_country.as_deref().unwrap_or("from_token");
        let url = format!(
            "https://api.spotify.com/v1/me/player?market={}&additional_types=track,episode",
            market
        );

        info!("🎯 Strategy 2: Player endpoint with market");
        info!("📍 URL: {}", url);

        let response = self.client
            .get(&url)
            .header("Authorization", format!("Bearer {}", token.access_token))
            .header("Accept", "application/json")
            .header("Accept-Language", "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7")
            .send()
            .await?;

        info!("📊 Response status: {}", response.status());

        if response.status() == 200 {
            let player_data: serde_json::Value = response.json().await?;
            
            if let Some(item) = player_data.get("item") {
                if let Ok(track) = serde_json::from_value::<SpotifyTrack>(item.clone()) {
                    let is_playing = player_data.get("is_playing")
                        .and_then(|v| v.as_bool())
                        .unwrap_or(false);
                    let progress_ms = player_data.get("progress_ms")
                        .and_then(|v| v.as_u64())
                        .unwrap_or(0);

                    info!("✅ Strategy 2 SUCCESS: Found track via player endpoint");
                    
                    return Ok(Some(TrackInfo {
                        id: track.id,
                        name: track.name,
                        artist: track.artists.into_iter()
                            .map(|a| a.name)
                            .collect::<Vec<_>>()
                            .join(", "),
                        album: AlbumInfo {
                            name: track.album.name,
                            images: track.album.images.into_iter()
                                .map(|img| ImageInfo {
                                    url: img.url,
                                    width: img.width,
                                    height: img.height,
                                })
                                .collect(),
                        },
                        duration_ms: track.duration_ms,
                        is_playing,
                        progress_ms,
                    }));
                }
            }
        }

        info!("⚠️ Strategy 2: No active playback");
        Ok(None)
    }

    async fn try_recently_played(&mut self) -> Result<Option<TrackInfo>> {
        let token = self.token.as_ref().ok_or_else(|| AppError::Config("No token".to_string()))?;
        
        info!("🎯 Strategy 3: Recently played tracks (last resort)");
        
        let response = self.client
            .get("https://api.spotify.com/v1/me/player/recently-played?limit=1")
            .header("Authorization", format!("Bearer {}", token.access_token))
            .header("Accept", "application/json")
            .send()
            .await?;

        if response.status() == 200 {
            let data: serde_json::Value = response.json().await?;
            
            if let Some(items) = data.get("items").and_then(|i| i.as_array()) {
                if let Some(first_item) = items.first() {
                    if let Some(track_data) = first_item.get("track") {
                        if let Ok(track) = serde_json::from_value::<SpotifyTrack>(track_data.clone()) {
                            info!("⚠️ Strategy 3: Found recently played track (not currently playing)");
                            
                            return Ok(Some(TrackInfo {
                                id: track.id,
                                name: format!("{} (Recently Played)", track.name),
                                artist: track.artists.into_iter()
                                    .map(|a| a.name)
                                    .collect::<Vec<_>>()
                                    .join(", "),
                                album: AlbumInfo {
                                    name: track.album.name,
                                    images: track.album.images.into_iter()
                                        .map(|img| ImageInfo {
                                            url: img.url,
                                            width: img.width,
                                            height: img.height,
                                        })
                                        .collect(),
                                },
                                duration_ms: track.duration_ms,
                                is_playing: false,
                                progress_ms: 0,
                            }));
                        }
                    }
                }
            }
        }

        info!("⚠️ Strategy 3: No recently played tracks found");
        Ok(None)
    }

    async fn check_devices_status(&mut self) {
        info!("🔍 Diagnostic: Checking available devices...");
        
        if let Some(token) = &self.token {
            if let Ok(response) = self.client
                .get("https://api.spotify.com/v1/me/player/devices")
                .header("Authorization", format!("Bearer {}", token.access_token))
                .send()
                .await
            {
                if response.status() == 200 {
                    if let Ok(devices_response) = response.json::<SpotifyDevicesResponse>().await {
                        if devices_response.devices.is_empty() {
                            error!("❌ CRITICAL: No devices found!");
                            error!("💡 Troubleshooting steps:");
                            error!("   1. Open Spotify Desktop or Web Player");
                            error!("   2. Play ANY song (even for 1 second)");
                            error!("   3. Wait 10 seconds");
                            error!("   4. Try again");
                        } else {
                            info!("📱 Available devices:");
                            for device in &devices_response.devices {
                                info!("   - {} ({}): {}", 
                                    device.name, 
                                    device.device_type,
                                    if device.is_active { "ACTIVE ✅" } else { "inactive" }
                                );
                            }
                            
                            if !devices_response.devices.iter().any(|d| d.is_active) {
                                warn!("⚠️ Devices found but none are ACTIVE");
                                warn!("💡 Play a song on Spotify to activate a device");
                            }
                        }
                    }
                }
            }
        }
    }

    fn convert_track_info(&self, track: SpotifyTrack, playing: SpotifyCurrentlyPlaying) -> Result<TrackInfo> {
        Ok(TrackInfo {
            id: track.id,
            name: track.name,
            artist: track.artists.into_iter()
                .map(|a| a.name)
                .collect::<Vec<_>>()
                .join(", "),
            album: AlbumInfo {
                name: track.album.name,
                images: track.album.images.into_iter()
                    .map(|img| ImageInfo {
                        url: img.url,
                        width: img.width,
                        height: img.height,
                    })
                    .collect(),
            },
            duration_ms: track.duration_ms,
            is_playing: playing.is_playing,
            progress_ms: playing.progress_ms.unwrap_or(0),
        })
    }

    pub async fn start_polling<F>(&mut self, mut callback: F) -> Result<()>
    where
        F: FnMut(Option<TrackInfo>) + Send + 'static,
    {
        info!("🎵 Starting Enhanced Spotify polling...");

        let mut last_track_id: Option<String> = None;
        let polling_interval = Duration::from_millis(self.config.spotify.polling_interval_ms);

        loop {
            match self.get_current_track().await {
                Ok(current_track) => {
                    let track_changed = match (&current_track, &last_track_id) {
                        (Some(track), Some(last_id)) => track.id != *last_id,
                        (Some(_), None) => true,
                        (None, Some(_)) => true,
                        (None, None) => false,
                    };

                    if track_changed {
                        last_track_id = current_track.as_ref().map(|t| t.id.clone());
                        debug!("🔄 Track changed or updated");
                    }

                    callback(current_track);
                }
                Err(e) => {
                    error!("❌ Error polling Spotify: {}", e);
                }
            }

            sleep(polling_interval).await;
        }
    }

    async fn authenticate(&mut self) -> Result<()> {
        info!("🔐 Starting Spotify OAuth authentication...");

        let auth_url = self.generate_auth_url();
        info!("🌐 Opening browser for Spotify authentication...");

        if let Err(e) = webbrowser::open(&auth_url) {
            warn!("⚠️ Failed to open browser automatically: {}", e);
            info!("📋 Please manually open this URL: {}", auth_url);
        }

        let code = self.start_callback_server().await?;
        let mut token = self.exchange_code_for_token(&code).await?;
        token.obtained_at = Some(std::time::Instant::now());
        self.token = Some(token);

        // Get user country after authentication
        if let Ok(user_data) = self.get_current_user().await {
            if let Some(country) = user_data.get("country").and_then(|c| c.as_str()) {
                self.user_country = Some(country.to_string());
                info!("🌍 User country: {}", country);
            }
        }

        info!("✅ Successfully authenticated with Spotify!");
        Ok(())
    }

    async fn start_callback_server(&self) -> Result<String> {
        let (tx, rx) = oneshot::channel();
        let tx = std::sync::Arc::new(std::sync::Mutex::new(Some(tx)));

        let callback = warp::path("callback")
            .and(warp::query::<HashMap<String, String>>())
            .map(move |params: HashMap<String, String>| {
                if let Some(code) = params.get("code") {
                    let mut tx_guard = tx.lock().unwrap();
                    if let Some(sender) = tx_guard.take() {
                        let _ = sender.send(code.clone());
                    }
                    warp::reply::html("✅ Authentication successful! You can close this window.".to_string())
                } else if let Some(error) = params.get("error") {
                    warp::reply::html(format!("❌ Authentication failed: {}", error))
                } else {
                    warp::reply::html("⚠️ Invalid callback parameters".to_string())
                }
            });

        let server = warp::serve(callback).run(([127, 0, 0, 1], 8888));
        tokio::spawn(server);

        info!("🌐 Callback server started on http://127.0.0.1:8888/callback");
        info!("⏳ Waiting for authorization...");

        let code = rx.await.map_err(|_| AppError::Config("Failed to receive authorization code".to_string()))?;
        Ok(code)
    }

    fn generate_auth_url(&self) -> String {
        let mut url = Url::parse("https://accounts.spotify.com/authorize").unwrap();

        let params = [
            ("client_id", &self.config.spotify.client_id),
            ("response_type", &"code".to_string()),
            ("redirect_uri", &self.config.spotify.redirect_uri),
            ("scope", &"user-read-playback-state user-read-currently-playing user-read-recently-played".to_string()),
        ];

        for (key, value) in &params {
            url.query_pairs_mut().append_pair(key, value);
        }

        url.to_string()
    }

    async fn exchange_code_for_token(&mut self, code: &str) -> Result<SpotifyToken> {
        let mut params = HashMap::new();
        params.insert("grant_type", "authorization_code");
        params.insert("code", code);
        params.insert("redirect_uri", &self.config.spotify.redirect_uri);

        let auth_header = base64::engine::general_purpose::STANDARD.encode(
            format!("{}:{}", self.config.spotify.client_id, self.config.spotify.client_secret)
        );

        let response = self.client
            .post("https://accounts.spotify.com/api/token")
            .header("Authorization", format!("Basic {}", auth_header))
            .header("Content-Type", "application/x-www-form-urlencoded")
            .form(&params)
            .send()
            .await?;

        if !response.status().is_success() {
            return Err(AppError::Config(format!(
                "Failed to exchange code for token: {}",
                response.status()
            )));
        }

        let token: SpotifyToken = response.json().await?;
        self.save_token(&token).await?;

        Ok(token)
    }

    pub async fn refresh_token(&mut self) -> Result<()> {
        info!("🔄 Refreshing Spotify token...");
        
        let current_token = self.token.as_ref()
            .ok_or_else(|| AppError::Config("No token to refresh".to_string()))?;
            
        let refresh_token = current_token.refresh_token.as_ref()
            .ok_or_else(|| AppError::Config("No refresh token available".to_string()))?;

        let mut params = HashMap::new();
        params.insert("grant_type", "refresh_token");
        params.insert("refresh_token", refresh_token);

        let auth_header = base64::engine::general_purpose::STANDARD.encode(
            format!("{}:{}", self.config.spotify.client_id, self.config.spotify.client_secret)
        );

        let response = self.client
            .post("https://accounts.spotify.com/api/token")
            .header("Authorization", format!("Basic {}", auth_header))
            .header("Content-Type", "application/x-www-form-urlencoded")
            .form(&params)
            .send()
            .await?;

        if !response.status().is_success() {
            let error_text = response.text().await?;
            return Err(AppError::Config(format!("Token refresh failed: {}", error_text)));
        }

        let mut new_token: SpotifyToken = response.json().await?;
        
        if new_token.refresh_token.is_none() {
            new_token.refresh_token = current_token.refresh_token.clone();
        }
        
        new_token.obtained_at = Some(std::time::Instant::now());
        self.token = Some(new_token.clone());
        self.save_token(&new_token).await?;
        
        info!("✅ Token refreshed successfully");
        Ok(())
    }

    pub async fn clear_token(&mut self) -> Result<()> {
        info!("🗑️ Clearing Spotify token...");
        
        self.token = None;
        
        let token_path = AppConfig::data_dir()?.join("spotify_token.json");
        if token_path.exists() {
            tokio::fs::remove_file(&token_path).await?;
            info!("✅ Token file deleted: {:?}", token_path);
        }
        
        info!("✅ Token cleared successfully");
        Ok(())
    }

    async fn get_current_user(&self) -> Result<serde_json::Value> {
        let token = self.token.as_ref()
            .ok_or_else(|| AppError::Config("No token available".to_string()))?;

        let response = self.client
            .get("https://api.spotify.com/v1/me")
            .header("Authorization", format!("Bearer {}", token.access_token))
            .send()
            .await?;

        if !response.status().is_success() {
            return Err(AppError::Config(format!(
                "Failed to get current user: {}",
                response.status()
            )));
        }

        Ok(response.json().await?)
    }

    async fn load_token(&self) -> Result<SpotifyToken> {
        let token_path = AppConfig::data_dir()?.join("spotify_token.json");

        if !token_path.exists() {
            return Err(AppError::Config("No saved token found".to_string()));
        }

        let content = tokio::fs::read_to_string(token_path).await?;
        let token: SpotifyToken = serde_json::from_str(&content)?;

        Ok(token)
    }

    async fn save_token(&self, token: &SpotifyToken) -> Result<()> {
        let data_dir = AppConfig::data_dir()?;
        tokio::fs::create_dir_all(&data_dir).await?;

        let token_path = data_dir.join("spotify_token.json");
        let content = serde_json::to_string_pretty(token)?;
        tokio::fs::write(&token_path, content).await?;
        
        info!("✅ Token saved to: {:?}", token_path);
        Ok(())
    }
}