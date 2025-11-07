// src-tauri/src/lib.rs

use tauri::Manager;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Track {
    pub name: String,
    pub artist: String,
    pub album: String,
    pub progress_ms: u64,
    pub duration_ms: u64,
}

#[tauri::command]
fn get_current_track() -> Result<Option<Track>, String> {
    // Implementação existente...
    Ok(None)
}

#[tauri::command]
fn get_lyrics(track: String, artist: String) -> Result<String, String> {
    // Implementação existente...
    Ok(String::new())
}

#[tauri::command]
fn get_sync_state() -> Result<u64, String> {
    // Implementação existente...
    Ok(0)
}

#[cfg(target_os = "windows")]
fn setup_transparent_window(window: &tauri::WebviewWindow) -> Result<(), Box<dyn std::error::Error>> {
    use windows::Win32::Foundation::{HWND, RECT};
    use windows::Win32::Graphics::Dwm::{DwmExtendFrameIntoClientArea, DwmEnableBlurBehindWindow, DWM_BLURBEHIND, DWM_BB_ENABLE, DWM_BB_BLURREGION};
    use windows::Win32::Graphics::Gdi::{CreateRectRgn, DeleteObject};
    use windows::Win32::UI::Controls::MARGINS;
    use windows::Win32::UI::WindowsAndMessaging::{
        GetWindowLongPtrW, SetWindowLongPtrW, SetWindowPos, GetClientRect,
        GWL_EXSTYLE, SWP_FRAMECHANGED, SWP_NOMOVE, SWP_NOSIZE, SWP_NOZORDER,
        WINDOW_EX_STYLE, WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_COMPOSITED,
    };

    unsafe {
        let hwnd = HWND(window.hwnd()?.0 as _);

        // 1. Configurar estilos estendidos da janela
        let mut ex_style = GetWindowLongPtrW(hwnd, GWL_EXSTYLE) as u32;
        ex_style |= WS_EX_LAYERED.0 | WS_EX_COMPOSITED.0;
        // NÃO adicionar WS_EX_TRANSPARENT aqui, pois queremos capturar cliques
        SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex_style as isize);

        // 2. Aplicar margens DWM para transparência total
        let margins = MARGINS {
            cxLeftWidth: -1,
            cxRightWidth: -1,
            cyTopHeight: -1,
            cyBottomHeight: -1,
        };
        DwmExtendFrameIntoClientArea(hwnd, &margins as *const _)?;

        // 3. Criar região de blur para o DWM (região vazia = transparente)
        let mut client_rect = RECT::default();
        GetClientRect(hwnd, &mut client_rect)?;
        
        // Criar região que cobre a janela inteira
        let hrgn = CreateRectRgn(0, 0, client_rect.right, client_rect.bottom);
        
        let mut bb = DWM_BLURBEHIND {
            dwFlags: DWM_BB_ENABLE | DWM_BB_BLURREGION,
            fEnable: true.into(),
            hRgnBlur: hrgn,
            fTransitionOnMaximized: false.into(),
        };
        
        DwmEnableBlurBehindWindow(hwnd, &bb)?;
        DeleteObject(hrgn)?;

        // 4. Forçar atualização da janela
        SetWindowPos(
            hwnd,
            HWND::default(),
            0,
            0,
            0,
            0,
            SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER,
        )?;

        println!("✅ Transparência Windows configurada com sucesso!");
    }

    Ok(())
}

#[cfg(not(target_os = "windows"))]
fn setup_transparent_window(_window: &tauri::WebviewWindow) -> Result<(), Box<dyn std::error::Error>> {
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            get_current_track,
            get_lyrics,
            get_sync_state
        ])
        .setup(|app| {
            // Configurar transparência assim que a janela for criada
            if let Some(window) = app.get_webview_window("main") {
                if let Err(e) = setup_transparent_window(&window) {
                    eprintln!("❌ Erro ao configurar transparência: {}", e);
                } else {
                    println!("🎯 Janela principal configurada para transparência");
                }
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("erro ao executar aplicação Tauri");
}
