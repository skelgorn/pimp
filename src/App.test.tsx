import { render, screen } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import App from './App';
import { useAppStore } from './store';

// Mock dos hooks do Tauri
vi.mock('./hooks/useTauri', () => ({
  useTauriCommands: vi.fn(() => ({
    getCurrentTrack: vi.fn(),
    getLyrics: vi.fn(),
    setSyncOffset: vi.fn(),
    resetSyncOffset: vi.fn(),
  })),
  useTauriEvents: vi.fn(),
  useKeyboardShortcuts: vi.fn(),
  useWindowDrag: vi.fn(() => ({ current: null })),
}));

// Mock do store
vi.mock('./store', async () => {
  const actual = await vi.importActual<any>('./store');
  return {
    ...actual,
    useAppStore: vi.fn(),
  };
});

// Mock do Framer Motion para evitar problemas de animação nos testes
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, className, ...props }: any) => (
      <div className={className} {...props}>
        {children}
      </div>
    ),
    button: ({ children, className, ...props }: any) => (
      <button className={className} {...props}>
        {children}
      </button>
    ),
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe('App Component', () => {
  const mockStore = {
    currentTrack: null,
    error: null,
    isConnected: false,
    lyrics: null,
    syncState: { global_offset: 0, is_paused: false },
    progress: 0,
    settings: {
      fontSize: 24,
      fontFamily: 'Arial',
      display: {
        showPreviousLine: true,
        showNextLine: true,
        animationDuration: 300,
      },
    },
    setError: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock padrão do store
    vi.mocked(useAppStore).mockImplementation((selector: any) => {
      if (selector === useAppStore.getState) {
        return { setError: mockStore.setError };
      }
      return selector ? selector(mockStore) : mockStore;
    });

    // Mock getState para o useEffect
    vi.mocked(useAppStore).getState = vi.fn(() => ({
      setError: mockStore.setError,
    })) as any;
  });

  it('renders the main app structure', () => {
    render(<App />);

    // Verifica estrutura principal
    expect(document.querySelector('.app-container')).toBeInTheDocument();
    
    // Verifica componente principal (apenas LyricsDisplay na UI minimalista)
    expect(screen.getByText('Waiting for music...')).toBeInTheDocument();
  });

  it.skip('shows connection status indicator when disconnected (UI removed for minimal design)', () => {
    // Este teste foi desabilitado porque ícones de conexão foram removidos da interface minimalista
  });

  it.skip('displays connected state when connected (UI removed for minimal design)', () => {
    // Este teste foi desabilitado porque a interface minimalista não mostra ícones de conexão
  });

  it.skip('displays error notification when error exists (UI removed for minimal design)', () => {
    // Este teste foi desabilitado porque a interface minimalista não mostra notificações de erro visíveis
  });

  it('does not display error notification when no error', () => {
    vi.mocked(useAppStore).mockImplementation((selector: any) => {
      const state = { ...mockStore, error: null };
      if (selector === useAppStore.getState) {
        return { setError: mockStore.setError };
      }
      return selector ? selector(state) : state;
    });

    render(<App />);

    // Não deve mostrar notificação de erro
    expect(screen.queryByText('Connection failed')).not.toBeInTheDocument();
  });

  it.skip('passes compact prop to TrackInfo when track exists (TrackInfo removed for minimal design)', () => {
    // Este teste foi desabilitado porque o componente TrackInfo foi removido da interface minimalista
  });

  it.skip('shows keyboard shortcuts hint in footer (footer removed for minimal design)', () => {
    // Este teste foi desabilitado porque o footer com atalhos foi removido da interface minimalista
  });

  it.skip('clears error after 5 seconds (error UI removed for minimal design)', () => {
    // Este teste foi desabilitado porque a interface minimalista não mostra erros visíveis
  });

  it('clears timeout when error changes', () => {
    vi.useFakeTimers();
    const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout');

    const { rerender } = render(<App />);

    // Primeiro, define um erro
    vi.mocked(useAppStore).mockImplementation((selector: any) => {
      const state = { ...mockStore, error: 'First error' };
      if (selector === useAppStore.getState) {
        return { setError: mockStore.setError };
      }
      return selector ? selector(state) : state;
    });

    rerender(<App />);

    // Depois, muda o erro
    vi.mocked(useAppStore).mockImplementation((selector: any) => {
      const state = { ...mockStore, error: 'Second error' };
      if (selector === useAppStore.getState) {
        return { setError: mockStore.setError };
      }
      return selector ? selector(state) : state;
    });

    rerender(<App />);

    // Verifica que clearTimeout foi chamado
    expect(clearTimeoutSpy).toHaveBeenCalled();

    vi.useRealTimers();
    clearTimeoutSpy.mockRestore();
  });

  it.skip('applies correct CSS classes for connection status (status UI removed for minimal design)', () => {
    // Este teste foi desabilitado porque ícones de conexão e badges foram removidos da interface minimalista
  });
});
