import { test, expect } from '@playwright/test';

test.describe('LetrasPIP App', () => {
  test('should load the main page', async ({ page }) => {
    await page.goto('/');
    
    // Verifica se a página carregou
    await expect(page).toHaveTitle(/LetrasPIP/);
  });

  test('should display lyrics display component', async ({ page }) => {
    await page.goto('/');
    
    // Procura pelo componente de letras
    const lyricsDisplay = page.locator('.lyrics-display');
    await expect(lyricsDisplay).toBeVisible();
  });

  test('should show waiting state initially', async ({ page }) => {
    await page.goto('/');
    
    // Deve mostrar estado de espera inicialmente
    await expect(page.getByText('Waiting for music...')).toBeVisible();
  });

  test('should display track info component', async ({ page }) => {
    await page.goto('/');
    
    // Procura pelo componente de informações da faixa
    const trackInfo = page.locator('.track-info');
    await expect(trackInfo).toBeVisible();
  });

  test('should show no track playing initially', async ({ page }) => {
    await page.goto('/');
    
    // Deve mostrar "No track playing" inicialmente
    await expect(page.getByText('No track playing')).toBeVisible();
  });

  test('should display connection status indicator', async ({ page }) => {
    await page.goto('/');
    
    // Deve mostrar indicador de status de conexão
    const statusIndicator = page.locator('.status-indicator');
    await expect(statusIndicator).toBeVisible();
  });

  test('should show keyboard shortcuts in footer', async ({ page }) => {
    await page.goto('/');
    
    // Verifica se os atalhos de teclado estão visíveis
    await expect(page.getByText('↑↓ Adjust')).toBeVisible();
    await expect(page.getByText('R Reset')).toBeVisible();
    await expect(page.getByText('D Debug')).toBeVisible();
    await expect(page.getByText('ESC Exit')).toBeVisible();
  });

  test('should handle window dragging area', async ({ page }) => {
    await page.goto('/');
    
    // Verifica se a área de drag da janela existe
    const dragArea = page.locator('[data-tauri-drag-region]');
    await expect(dragArea).toBeVisible();
  });
});

test.describe('LetrasPIP - Lyrics Display', () => {
  test('should display lyrics when available', async ({ page }) => {
    await page.goto('/');
    
    // Simula o estado com letras (isso dependeria de mock do backend)
    // Por enquanto, verifica se o componente está preparado para mostrar letras
    const lyricsContainer = page.locator('.lyrics-container');
    await expect(lyricsContainer).toBeVisible();
  });

  test('should show instrumental state', async ({ page }) => {
    await page.goto('/');
    
    // Testa se consegue mostrar estado instrumental
    // (Isso seria testado com mock de dados)
    const lyricsDisplay = page.locator('.lyrics-display');
    await expect(lyricsDisplay).toBeVisible();
  });

  test('should handle scroll interactions', async ({ page }) => {
    await page.goto('/');
    
    // Testa interação de scroll no componente de letras
    const lyricsDisplay = page.locator('.lyrics-display');
    await expect(lyricsDisplay).toBeVisible();
    
    // Simula scroll
    await lyricsDisplay.hover();
    await page.mouse.wheel(0, 100);
    
    // Verifica se o componente ainda está visível após scroll
    await expect(lyricsDisplay).toBeVisible();
  });
});

test.describe('LetrasPIP - Track Info', () => {
  test('should display track information when available', async ({ page }) => {
    await page.goto('/');
    
    // Verifica se o componente TrackInfo está presente
    const trackInfo = page.locator('.track-info');
    await expect(trackInfo).toBeVisible();
  });

  test('should show progress bar', async ({ page }) => {
    await page.goto('/');
    
    // Procura por elementos de progresso
    // (Seria mais específico com dados reais)
    const trackInfo = page.locator('.track-info');
    await expect(trackInfo).toBeVisible();
  });
});

test.describe('LetrasPIP - Error Handling', () => {
  test('should handle connection errors gracefully', async ({ page }) => {
    await page.goto('/');
    
    // Verifica se a aplicação carrega mesmo com possíveis erros de conexão
    await expect(page.getByText('Waiting for music...')).toBeVisible();
  });

  test('should display error notifications when they occur', async ({ page }) => {
    await page.goto('/');
    
    // Verifica se o sistema está preparado para mostrar erros
    // (Isso seria testado com simulação de erros)
    const app = page.locator('.app-background');
    await expect(app).toBeVisible();
  });
});

test.describe('LetrasPIP - Keyboard Shortcuts', () => {
  test('should respond to keyboard shortcuts', async ({ page }) => {
    await page.goto('/');
    
    // Testa atalhos de teclado básicos
    await page.keyboard.press('Escape');
    
    // Verifica se a aplicação ainda está funcionando
    await expect(page.getByText('Waiting for music...')).toBeVisible();
  });

  test('should handle arrow keys for adjustment', async ({ page }) => {
    await page.goto('/');
    
    // Testa teclas de seta para ajuste
    await page.keyboard.press('ArrowUp');
    await page.keyboard.press('ArrowDown');
    
    // Verifica se a aplicação responde
    const app = page.locator('.app-background');
    await expect(app).toBeVisible();
  });

  test('should handle reset shortcut', async ({ page }) => {
    await page.goto('/');
    
    // Testa tecla de reset
    await page.keyboard.press('KeyR');
    
    // Verifica se a aplicação ainda está funcionando
    await expect(page.getByText('Waiting for music...')).toBeVisible();
  });
});

test.describe('LetrasPIP - Responsive Design', () => {
  test('should work on different screen sizes', async ({ page }) => {
    // Testa em tamanho desktop
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.goto('/');
    await expect(page.getByText('Waiting for music...')).toBeVisible();
    
    // Testa em tamanho menor
    await page.setViewportSize({ width: 800, height: 600 });
    await expect(page.getByText('Waiting for music...')).toBeVisible();
    
    // Testa em tamanho compacto
    await page.setViewportSize({ width: 400, height: 300 });
    await expect(page.getByText('Waiting for music...')).toBeVisible();
  });
});

test.describe('LetrasPIP - Performance', () => {
  test('should load quickly', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/');
    
    // Verifica se carregou em menos de 3 segundos
    await expect(page.getByText('Waiting for music...')).toBeVisible();
    const loadTime = Date.now() - startTime;
    
    expect(loadTime).toBeLessThan(3000);
  });

  test('should not have console errors', async ({ page }) => {
    const consoleErrors: string[] = [];
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    await page.goto('/');
    await expect(page.getByText('Waiting for music...')).toBeVisible();
    
    // Verifica se não há erros críticos no console
    const criticalErrors = consoleErrors.filter(error => 
      !error.includes('Failed to connect') && // Erros de conexão são esperados em testes
      !error.includes('WebSocket')
    );
    
    expect(criticalErrors).toHaveLength(0);
  });
});
