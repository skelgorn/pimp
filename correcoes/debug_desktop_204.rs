// Helper para diagnosticar exatamente por que o Desktop retorna 204

impl SpotifyClient {
    /// Diagnóstico completo do estado do Desktop
    pub async fn diagnose_desktop_204(&self) -> Result<()> {
        info!("🔍 STARTING DESKTOP 204 DIAGNOSIS");
        info!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
        
        // 1. Verifica token
        info!("1️⃣ Checking token...");
        let token = self.get_token()?;
        info!("   Token length: {}", token.len());
        info!("   Token prefix: {}...", &token[..20.min(token.len())]);
        
        // 2. Verifica devices
        info!("2️⃣ Checking devices...");
        let devices_response = self.client
            .get("https://api.spotify.com/v1/me/player/devices")
            .bearer_auth(&token)
            .send()
            .await?;
        
        info!("   Status: {}", devices_response.status());
        let devices_json: serde_json::Value = devices_response.json().await?;
        info!("   Devices response: {}", serde_json::to_string_pretty(&devices_json)?);
        
        if let Some(devices) = devices_json["devices"].as_array() {
            for (i, device) in devices.iter().enumerate() {
                info!("   Device {}: ", i + 1);
                info!("     - Name: {}", device["name"].as_str().unwrap_or("N/A"));
                info!("     - Type: {}", device["type"].as_str().unwrap_or("N/A"));
                info!("     - Active: {}", device["is_active"].as_bool().unwrap_or(false));
                info!("     - Volume: {}", device["volume_percent"].as_u64().unwrap_or(0));
                info!("     - ID: {}", device["id"].as_str().unwrap_or("N/A"));
            }
        }
        
        // 3. Testa currently-playing com máximo de headers
        info!("3️⃣ Testing currently-playing endpoint...");
        let cp_response = self.client
            .get("https://api.spotify.com/v1/me/player/currently-playing")
            .bearer_auth(&token)
            .query(&[
                ("market", "from_token"),
                ("additional_types", "track,episode"),
            ])
            .header("Accept", "application/json")
            .header("Accept-Language", "en-US,en;q=0.9")
            .header("User-Agent", "LetrasPIP/1.0")
            .send()
            .await?;
        
        let status = cp_response.status();
        let headers = cp_response.headers().clone();
        
        info!("   Status: {}", status);
        info!("   Headers received:");
        for (key, value) in headers.iter() {
            info!("     {}: {:?}", key, value);
        }
        
        if status == 204 {
            warn!("   ⚠️ Got 204 - No content");
            info!("   This means Spotify API says: 'Nothing is playing'");
        } else if status == 200 {
            let body = cp_response.text().await?;
            info!("   Body length: {}", body.len());
            if !body.is_empty() {
                info!("   Body preview: {}", &body[..body.len().min(200)]);
            }
        }
        
        // 4. Testa player endpoint completo
        info!("4️⃣ Testing full player endpoint...");
        let player_response = self.client
            .get("https://api.spotify.com/v1/me/player")
            .bearer_auth(&token)
            .send()
            .await?;
        
        info!("   Status: {}", player_response.status());
        if player_response.status() == 200 {
            let json: serde_json::Value = player_response.json().await?;
            info!("   Player state: {}", serde_json::to_string_pretty(&json)?);
        }
        
        // 5. Testa recently-played
        info!("5️⃣ Testing recently-played...");
        let recent_response = self.client
            .get("https://api.spotify.com/v1/me/player/recently-played?limit=1")
            .bearer_auth(&token)
            .send()
            .await?;
        
        info!("   Status: {}", recent_response.status());
        if recent_response.status() == 200 {
            let json: serde_json::Value = recent_response.json().await?;
            info!("   Recently played: {}", serde_json::to_string_pretty(&json)?);
        }
        
        // 6. Recomendações
        info!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
        info!("💡 RECOMMENDATIONS:");
        
        if let Some(devices) = devices_json["devices"].as_array() {
            let active_desktop = devices.iter().any(|d| 
                d["type"] == "Computer" && d["is_active"].as_bool().unwrap_or(false)
            );
            
            if !active_desktop {
                warn!("   ⚠️ No active Desktop device found!");
                info!("   → Make sure Spotify Desktop is playing music");
            } else {
                info!("   ✅ Active Desktop device found");
                
                if status == 204 {
                    warn!("   ⚠️ But API returns 204. Possible causes:");
                    info!("   1. Song just ended (wait for next song)");
                    info!("   2. Player is paused (press play)");
                    info!("   3. Desktop hasn't synced state yet (wait 5-10s)");
                    info!("   4. API cache issue (try switching songs)");
                    info!("   ");
                    info!("   🔧 Try this:");
                    info!("   - Pause and play again");
                    info!("   - Skip to next song");
                    info!("   - Wait 10 seconds and try again");
                }
            }
        }
        
        info!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
        Ok(())
    }
    
    /// Força uma "piscada" no player para acordá-lo
    pub async fn force_player_refresh(&self) -> Result<()> {
        info!("🔄 Forcing player refresh...");
        
        // Pega o estado atual
        let player_response = self.client
            .get("https://api.spotify.com/v1/me/player")
            .bearer_auth(&self.get_token()?)
            .send()
            .await?;
        
        if player_response.status() == 200 {
            let json: serde_json::Value = player_response.json().await?;
            
            if let Some(progress) = json["progress_ms"].as_u64() {
                // Faz um "seek" para a posição atual
                // Isso força o Spotify a atualizar o estado
                info!("   Seeking to current position: {}ms", progress);
                
                let seek_response = self.client
                    .put("https://api.spotify.com/v1/me/player/seek")
                    .bearer_auth(&self.get_token()?)
                    .query(&[("position_ms", progress.to_string())])
                    .send()
                    .await?;
                
                info!("   Seek response: {}", seek_response.status());
                
                if seek_response.status().is_success() {
                    tokio::time::sleep(Duration::from_millis(500)).await;
                    info!("✅ Player refreshed successfully");
                    return Ok(());
                }
            }
        }
        
        warn!("⚠️ Could not refresh player");
        Ok(())
    }
}

// Adicione um comando Tauri para testar
#[tauri::command]
async fn diagnose_desktop(state: State<'_, AppState>) -> Result<String, String> {
    let spotify = state.spotify.lock().await;
    
    match spotify.diagnose_desktop_204().await {
        Ok(_) => Ok("Diagnosis completed. Check logs.".to_string()),
        Err(e) => Err(format!("Diagnosis failed: {}", e)),
    }
}

#[tauri::command]
async fn force_refresh_player(state: State<'_, AppState>) -> Result<String, String> {
    let spotify = state.spotify.lock().await;
    
    match spotify.force_player_refresh().await {
        Ok(_) => Ok("Player refreshed".to_string()),
        Err(e) => Err(format!("Refresh failed: {}", e)),
    }
}
