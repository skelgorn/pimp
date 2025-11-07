// ALTERNATIVA: Se a primeira solução não funcionar, use este código

#[cfg(target_os = "windows")]
fn setup_transparent_window_alternative(window: &tauri::WebviewWindow) -> Result<(), Box<dyn std::error::Error>> {
    use windows::Win32::Foundation::{HWND, COLORREF};
    use windows::Win32::UI::WindowsAndMessaging::{
        GetWindowLongPtrW, SetWindowLongPtrW, SetLayeredWindowAttributes,
        GWL_EXSTYLE, LWA_COLORKEY, LWA_ALPHA,
        WINDOW_EX_STYLE, WS_EX_LAYERED, WS_EX_COMPOSITED,
    };
    use windows::Win32::Graphics::Dwm::{DwmExtendFrameIntoClientArea};
    use windows::Win32::UI::Controls::MARGINS;

    unsafe {
        let hwnd = HWND(window.hwnd()?.0 as _);

        // 1. Configurar janela como layered
        let mut ex_style = GetWindowLongPtrW(hwnd, GWL_EXSTYLE) as u32;
        ex_style |= WS_EX_LAYERED.0 | WS_EX_COMPOSITED.0;
        SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex_style as isize);

        // 2. Definir cor transparente (preto = 0x00000000)
        // Qualquer pixel preto no WebView será transparente
        let transparent_color = COLORREF(0x00000000);
        SetLayeredWindowAttributes(
            hwnd,
            transparent_color,
            255, // Alpha máximo para conteúdo não-preto
            LWA_COLORKEY | LWA_ALPHA,
        )?;

        // 3. Estender frame DWM
        let margins = MARGINS {
            cxLeftWidth: -1,
            cxRightWidth: -1,
            cyTopHeight: -1,
            cyBottomHeight: -1,
        };
        DwmExtendFrameIntoClientArea(hwnd, &margins as *const _)?;

        println!("✅ Transparência Windows (layered) configurada!");
    }

    Ok(())
}

// IMPORTANTE: Se usar esta abordagem, o CSS deve ter background: #000000 (preto)
// ao invés de transparent, pois o preto será a cor de transparência
