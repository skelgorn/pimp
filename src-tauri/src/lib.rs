mod spotify;
mod lyrics;
mod sync_engine;
mod cache;
mod config;
mod types;
mod offset_manager;

use tauri::{Manager, State};
use std::sync::Arc;
use tokio::sync::Mutex;
use tracing::info;

use crate::spotify::SpotifyClient;
use crate::sync_engine::SyncEngine;
use crate::offset_manager::OffsetManager;
use crate::types::{Result, LyricsData, SyncState, AppError};

#[tauri::command]
async fn get_current_track(state: State<'_, AppState>) -> Result<Option<crate::types::TrackInfo>> {
    info!("🎵 TAURI COMMAND: get_current_track called");
    
    let spotify_result = tokio::time::timeout(
        tokio::time::Duration::from_secs(5),
        state.spotify.lock()
    ).await;
    
    match spotify_result {
        Ok(mut spotify) => {
            info!("🎵 TAURI COMMAND: got spotify lock");
            let result = spotify.get_current_track().await;
            info!("🎵 TAURI COMMAND: spotify.get_current_track() returned: {:?}", result.is_ok());
            
            if let Ok(Some(track)) = &result {
                let mut sync_engine = state.sync_engine.lock().await;
                if let Err(e) = sync_engine.update_track(track.clone()).await {
                    info!("⚠️ Failed to update sync engine: {:?}", e);
                }
            }
            
            result
        }
        Err(_) => {
            info!("🎵 TAURI COMMAND: timeout waiting for spotify lock");
            Err(AppError::Config("Timeout waiting for Spotify lock".to_string()))
        }
    }
}

#[tauri::command]
async fn get_lyrics(artist: String, title: String, state: tauri::State<'_, AppState>) -> Result<Option<LyricsData>> {
    let mut sync_engine = state.sync_engine.lock().await;
    sync_engine.fetch_lyrics(&artist, &title).await
}

#[tauri::command]
async fn reset_offset(state: tauri::State<'_, AppState>) -> Result<i32> {
    let mut sync_engine = state.sync_engine.lock().await;
    sync_engine.reset_offset().await
}

#[tauri::command]
async fn get_sync_state(state: tauri::State<'_, AppState>) -> Result<SyncState> {
    let sync_engine = state.sync_engine.lock().await;
    Ok(sync_engine.get_state().await)
}

#[tauri::command]
async fn adjust_offset(track_id: String, offset_delta: i32, state: tauri::State<'_, AppState>) -> Result<()> {
    info!("🎯 TAURI COMMAND: adjust_offset called - track: {}, delta: {}ms", track_id, offset_delta);
    
    let current_offset = state.offset_manager.get_global_offset(&track_id).await;
    let new_offset = current_offset + offset_delta;
    
    state.offset_manager.set_global_offset(&track_id, new_offset).await?;
    
    info!("✅ Global offset adjusted: {} -> {}ms", current_offset, new_offset);
    Ok(())
}

#[tauri::command]
async fn force_refresh_token(state: tauri::State<'_, AppState>) -> Result<()> {
    info!("🔄 TAURI COMMAND: force_refresh_token called");
    
    let mut spotify = state.spotify.lock().await;
    spotify.refresh_token().await?;
    
    info!("✅ Token refreshed successfully");
    Ok(())
}



// App State
#[derive(Clone)]
struct AppState {
    spotify: Arc<Mutex<SpotifyClient>>,
    sync_engine: Arc<Mutex<SyncEngine>>,
    offset_manager: Arc<OffsetManager>,
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tracing_subscriber::fmt::init();
    info!("Starting LetrasPIP Tauri...");

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_global_shortcut::Builder::default().build())
        .plugin(tauri_plugin_notification::init())
        .setup(|app| {
            let spotify_client = SpotifyClient::new();
            let sync_engine = SyncEngine::new().with_app_handle(app.handle().clone());
            
            let cache_dir = app.path().app_cache_dir().unwrap_or_else(|_| {
                std::env::current_dir().unwrap().join("cache")
            });
            let offset_manager = OffsetManager::new(cache_dir);

            let app_state = AppState {
                spotify: Arc::new(Mutex::new(spotify_client)),
                sync_engine: Arc::new(Mutex::new(sync_engine)),
                offset_manager: Arc::new(offset_manager),
            };

            app.manage(app_state.clone());

            let offset_manager_clone = app_state.offset_manager.clone();
            tauri::async_runtime::spawn(async move {
                if let Err(e) = offset_manager_clone.initialize().await {
                    info!("Offset manager initialization failed: {}", e);
                } else {
                    info!("Offset manager initialized successfully");
                }
            });

            let spotify_clone = app_state.spotify.clone();
            tauri::async_runtime::spawn(async move {
                let mut spotify = spotify_clone.lock().await;
                if let Err(e) = spotify.initialize().await {
                    info!("Spotify initialization failed: {}", e);
                } else {
                    info!("Spotify initialized successfully");
                    drop(spotify);
                    info!("Backend initialized - frontend will handle polling");
                }
            });

            info!("LetrasPIP initialized successfully");
            
            // Abrir DevTools em modo debug
            #[cfg(debug_assertions)]
            {
                use tauri::Manager;
                if let Some(window) = app.get_webview_window("main") {
                    window.open_devtools();
                    info!("🔍 DevTools opened");
                }
            }
            
            // Configurar transparência do Windows com delay para garantir timing correto
            #[cfg(target_os = "windows")]
            {
                use tauri::Manager;
                let app_handle = app.handle().clone();
                tauri::async_runtime::spawn(async move {
                    tokio::time::sleep(std::time::Duration::from_millis(200)).await;
                    if let Some(window) = app_handle.get_webview_window("main") {
                        use windows::Win32::Foundation::{HWND, COLORREF, RECT};
                        use windows::Win32::Graphics::Dwm::DwmExtendFrameIntoClientArea;
                        use windows::Win32::Graphics::Gdi::{CreateRectRgn, SetWindowRgn};
                        use windows::Win32::UI::Controls::MARGINS;
                        use windows::Win32::UI::WindowsAndMessaging::{
                            GetWindowLongPtrW, SetWindowLongPtrW, SetLayeredWindowAttributes, 
                            GetClientRect, GWL_EXSTYLE, LWA_COLORKEY, LWA_ALPHA, 
                            WS_EX_LAYERED, WS_EX_COMPOSITED,
                        };
                        unsafe {
                            let hwnd = HWND(window.hwnd().unwrap().0 as _);
                            let mut rect = RECT::default();
                            let _ = GetClientRect(hwnd, &mut rect);
                            let hrgn = CreateRectRgn(0, 0, rect.right, rect.bottom);
                            let _ = SetWindowRgn(hwnd, hrgn, true);
                            let mut ex_style = GetWindowLongPtrW(hwnd, GWL_EXSTYLE) as u32;
                            ex_style |= WS_EX_LAYERED.0 | WS_EX_COMPOSITED.0;
                            SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex_style as isize);
                            let margins = MARGINS {
                                cxLeftWidth: -1,
                                cxRightWidth: -1,
                                cyTopHeight: -1,
                                cyBottomHeight: -1,
                            };
                            let _ = DwmExtendFrameIntoClientArea(hwnd, &margins as *const _);
                            let transparent_color = COLORREF(0x00000000);
                            let _ = SetLayeredWindowAttributes(
                                hwnd,
                                transparent_color,
                                255,
                                LWA_COLORKEY | LWA_ALPHA,
                            );
                        }
                    }
                });
            }
            
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_current_track,
            get_lyrics,
            adjust_offset,
            reset_offset,
            get_sync_state,
            force_refresh_token
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
