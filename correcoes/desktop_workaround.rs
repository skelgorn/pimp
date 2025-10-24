// SOLUÇÃO PARA SPOTIFY DESKTOP - Problema de Timing/Sincronização
// O Desktop precisa de um "warm-up" antes de responder corretamente

use std::sync::Arc;
use tokio::sync::RwLock;
use std::time::{Duration, Instant};

#[derive(Clone, Debug)]
struct DesktopState {
    is_warmed_up: bool,
    last_successful_call: Option<Instant>,
    consecutive_204s: u32,
}

impl SpotifyClient {
    // Adicione este campo na struct SpotifyClient
    // desktop_state: Arc<RwLock<DesktopState>>,
    
    /// Método específico para "acordar" o Desktop
    async fn wake_up_desktop(&self) -> Result<()> {
        info!("🔔 Waking up Spotify Desktop...");
        
        // Sequência de chamadas para "acordar" a API do Desktop
        let endpoints = vec![
            "https://api.spotify.com/v1/me/player/devices",
            "https://api.spotify.com/v1/me/player",
            "https://api.spotify.com/v1/me/player/currently-playing",
        ];
        
        for endpoint in endpoints {
            let _ = self.client
                .get(endpoint)
                .bearer_auth(&self.get_token()?)
                .timeout(Duration::from_secs(3))
                .send()
                .await;
            
            tokio::time::sleep(Duration::from_millis(200)).await;
        }
        
        info!("✅ Desktop wake-up sequence completed");
        Ok(())
    }
    
    /// Estratégia otimizada para Desktop com warm-up
    pub async fn get_current_track_desktop(&self) -> Result<Option<TrackInfo>> {
        let mut state = self.desktop_state.write().await;
        
        // Se ainda não aquecemos ou temos muitos 204s, faz warm-up
        if !state.is_warmed_up || state.consecutive_204s > 3 {
            drop(state); // Release lock
            self.wake_up_desktop().await?;
            state = self.desktop_state.write().await;
            state.is_warmed_up = true;
            state.consecutive_204s = 0;
        }
        
        drop(state); // Release lock para as chamadas
        
        // Estratégia 1: Currently-playing com headers otimizados
        info!("🎯 Desktop Strategy 1: Currently-playing");
        match self.desktop_currently_playing().await {
            Ok(Some(track)) => {
                let mut state = self.desktop_state.write().await;
                state.consecutive_204s = 0;
                state.last_successful_call = Some(Instant::now());
                return Ok(Some(track));
            }
            Ok(None) => {
                let mut state = self.desktop_state.write().await;
                state.consecutive_204s += 1;
            }
            Err(_) => {}
        }
        
        // Pequeno delay entre estratégias
        tokio::time::sleep(Duration::from_millis(150)).await;
        
        // Estratégia 2: Player endpoint completo
        info!("🎯 Desktop Strategy 2: Full player");
        match self.desktop_full_player().await {
            Ok(Some(track)) => {
                let mut state = self.desktop_state.write().await;
                state.consecutive_204s = 0;
                state.last_successful_call = Some(Instant::now());
                return Ok(Some(track));
            }
            Ok(None) => {
                let mut state = self.desktop_state.write().await;
                state.consecutive_204s += 1;
            }
            Err(_) => {}
        }
        
        // Estratégia 3: Retry com exponential backoff
        info!("🎯 Desktop Strategy 3: Retry with backoff");
        for attempt in 1..=3 {
            tokio::time::sleep(Duration::from_millis(attempt * 200)).await;
            
            if let Ok(Some(track)) = self.desktop_currently_playing().await {
                let mut state = self.desktop_state.write().await;
                state.consecutive_204s = 0;
                state.last_successful_call = Some(Instant::now());
                info!("✅ Desktop succeeded on retry {}", attempt);
                return Ok(Some(track));
            }
        }
        
        warn!("⚠️ Desktop: All strategies returned 204");
        Ok(None)
    }
    
    async fn desktop_currently_playing(&self) -> Result<Option<TrackInfo>> {
        let response = self.client
            .get("https://api.spotify.com/v1/me/player/currently-playing")
            .bearer_auth(&self.get_token()?)
            .query(&[
                ("market", "from_token"),
                ("additional_types", "track,episode"),
            ])
            .header("Accept", "application/json")
            .header("Content-Type", "application/json")
            .timeout(Duration::from_secs(5))
            .send()
            .await?;
        
        let status = response.status();
        info!("📊 Currently-playing status: {}", status);
        
        if status == 204 {
            return Ok(None);
        }
        
        if status == 200 {
            let text = response.text().await?;
            
            // Debug: mostra o tamanho da resposta
            info!("📦 Response size: {} bytes", text.len());
            
            if text.is_empty() {
                warn!("⚠️ Got 200 but empty body");
                return Ok(None);
            }
            
            match serde_json::from_str::<serde_json::Value>(&text) {
                Ok(json) => {
                    info!("✅ Successfully parsed JSON");
                    return self.parse_track_from_json(&json);
                }
                Err(e) => {
                    error!("❌ Failed to parse JSON: {}", e);
                    error!("📄 Response text: {}", &text[..text.len().min(500)]);
                    return Ok(None);
                }
            }
        }
        
        Ok(None)
    }
    
    async fn desktop_full_player(&self) -> Result<Option<TrackInfo>> {
        let response = self.client
            .get("https://api.spotify.com/v1/me/player")
            .bearer_auth(&self.get_token()?)
            .query(&[
                ("market", "from_token"),
                ("additional_types", "track,episode"),
            ])
            .timeout(Duration::from_secs(5))
            .send()
            .await?;
        
        let status = response.status();
        info!("📊 Full player status: {}", status);
        
        if status == 204 {
            return Ok(None);
        }
        
        if status == 200 {
            let json: serde_json::Value = response.json().await?;
            
            // O endpoint /player retorna o item dentro de "item"
            if let Some(item) = json.get("item") {
                let mut track_json = json.clone();
                // Move os campos do player para o nível correto
                if let Some(is_playing) = json.get("is_playing") {
                    track_json["is_playing"] = is_playing.clone();
                }
                if let Some(progress) = json.get("progress_ms") {
                    track_json["progress_ms"] = progress.clone();
                }
                
                return self.parse_track_from_json(&track_json);
            }
        }
        
        Ok(None)
    }
}

// Modifique o get_current_track principal para usar esta lógica
pub async fn get_current_track(&self) -> Result<Option<TrackInfo>> {
    // Verifica se tem dispositivo ativo
    let devices_response = self.client
        .get("https://api.spotify.com/v1/me/player/devices")
        .bearer_auth(&self.get_token()?)
        .send()
        .await?;
    
    let mut is_desktop_active = false;
    if devices_response.status().is_success() {
        if let Ok(json) = devices_response.json::<serde_json::Value>().await {
            if let Some(devices) = json["devices"].as_array() {
                for device in devices {
                    if device["is_active"].as_bool().unwrap_or(false) {
                        let device_type = device["type"].as_str().unwrap_or("");
                        let device_name = device["name"].as_str().unwrap_or("Unknown");
                        
                        info!("🎧 Active device: {} ({})", device_name, device_type);
                        
                        // Desktop = tipo "Computer"
                        if device_type == "Computer" {
                            is_desktop_active = true;
                        }
                        break;
                    }
                }
            }
        }
    }
    
    if is_desktop_active {
        info!("🖥️ Using Desktop-optimized strategy");
        return self.get_current_track_desktop().await;
    } else {
        info!("🌐 Using Web Player strategy");
        // Sua lógica normal para Web Player
        return self.get_current_track_web().await;
    }
}

// Mantenha sua lógica atual como get_current_track_web
async fn get_current_track_web(&self) -> Result<Option<TrackInfo>> {
    // Cole aqui sua implementação atual de get_current_track
    // que funciona bem com o Web Player
    
    info!("🎯 Strategy 1: Enhanced currently-playing endpoint");
    let response = self.client
        .get("https://api.spotify.com/v1/me/player/currently-playing")
        .bearer_auth(&self.get_token()?)
        .query(&[
            ("market", "from_token"),
            ("additional_types", "track,episode"),
        ])
        .send()
        .await?;
    
    if response.status() == 200 {
        let json: serde_json::Value = response.json().await?;
        if let Some(track) = self.parse_track_from_json(&json)? {
            return Ok(Some(track));
        }
    }
    
    // ... resto das suas estratégias para Web Player
    Ok(None)
}
