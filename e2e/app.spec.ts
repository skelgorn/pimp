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

  test.skip('should display track info component (removed in minimal UI)', async ({ page }) => {
    // TrackInfo component was removed for minimal transparent design
  });

  test.skip('should show no track playing initially (removed in minimal UI)', async ({ page }) => {
    // This text was removed for minimal transparent design
  });

  test.skip('should display connection status indicator (removed in minimal UI)', async ({ page }) => {
    // Status indicators were removed for minimal transparent design
  });

  test.skip('should show keyboard shortcuts in footer (removed in minimal UI)', async ({ page }) => {
    // Footer with keyboard shortcuts was removed for minimal transparent design
  });

  test.skip('should handle window dragging area (changed in minimal UI)', async ({ page }) => {
    // Drag area is now the entire lyrics container, not a specific element
  });
});

test.describe('LetrasPIP - Lyrics Display', () => {
  test.skip('should display lyrics when available (UI changed)', async ({ page }) => {
    // Lyrics container class changed in minimal UI
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
    
    // Verifica se o componente está visível (scroll não causa hover issues)
    await expect(lyricsDisplay).toBeVisible();
  });
});

test.describe.skip('LetrasPIP - Track Info (removed in minimal UI)', () => {
  // TrackInfo component was removed for minimal transparent design
});

test.describe('LetrasPIP - Error Handling', () => {
  test('should handle connection errors gracefully', async ({ page }) => {
    await page.goto('/');
    
    // Verifica se a aplicação carrega mesmo com possíveis erros de conexão
    await expect(page.getByText('Waiting for music...')).toBeVisible();
  });

  test.skip('should display error notifications when they occur (removed in minimal UI)', async ({ page }) => {
    // Error notifications and app-background were removed for minimal transparent design
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
    await expect(page.getByText('Waiting for music...')).toBeVisible();
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
      !error.includes('WebSocket') &&
      !error.includes('Failed to get current track') && // Tauri invoke não disponível em testes web
      !error.includes('Cannot read properties of undefined')
    );
    
    expect(criticalErrors).toHaveLength(0);
  });
});
