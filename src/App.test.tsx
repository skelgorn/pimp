import { render, screen, act } from '@testing-library/react';
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
    expect(document.querySelector('.app-background')).toBeInTheDocument();
    
    // Verifica componentes principais
    expect(screen.getByText('No track playing')).toBeInTheDocument(); // TrackInfo
    expect(screen.getByText('Waiting for music...')).toBeInTheDocument(); // LyricsDisplay
  });

  it('shows connection status indicator when disconnected', () => {
    vi.mocked(useAppStore).mockImplementation((selector: any) => {
      const state = { ...mockStore, isConnected: false, syncState: { ...mockStore.syncState, global_offset: -100 } };
      if (selector === useAppStore.getState) {
        return { setError: mockStore.setError };
      }
      return selector ? selector(state) : state;
    });

    render(<App />);

    // Deve mostrar ícone de desconectado
    const wifiOffIcon = document.querySelector('.lucide-wifi-off');
    expect(wifiOffIcon).toBeInTheDocument();
  });

  it('shows connection status indicator when connected', () => {
    vi.mocked(useAppStore).mockImplementation((selector: any) => {
      const state = { ...mockStore, isConnected: true, syncState: { ...mockStore.syncState, global_offset: 100 } };
      if (selector === useAppStore.getState) {
        return { setError: mockStore.setError };
      }
      return selector ? selector(state) : state;
    });

    render(<App />);

    // Deve mostrar ícone de conectado
    const wifiIcon = document.querySelector('.lucide-wifi');
    expect(wifiIcon).toBeInTheDocument();
  });

  it('displays error notification when error exists', () => {
    vi.mocked(useAppStore).mockImplementation((selector: any) => {
      const state = { ...mockStore, error: 'Connection failed' };
      if (selector === useAppStore.getState) {
        return { setError: mockStore.setError };
      }
      return selector ? selector(state) : state;
    });

    render(<App />);

    // Deve mostrar notificação de erro
    expect(screen.getByText('Connection failed')).toBeInTheDocument();
    
    // Deve mostrar ícone de alerta (pode estar mockado como div)
    const errorNotification = screen.getByText('Connection failed').closest('div');
    expect(errorNotification).toBeInTheDocument();
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

  it('passes compact prop to TrackInfo when track exists', () => {
    const mockTrack = {
      name: 'Test Song',
      artist: 'Test Artist',
      album: { name: 'Test Album', images: [] },
      duration_ms: 180000,
      is_playing: true,
    };

    vi.mocked(useAppStore).mockImplementation((selector: any) => {
      const state = { ...mockStore, currentTrack: mockTrack };
      if (selector === useAppStore.getState) {
        return { setError: mockStore.setError };
      }
      return selector ? selector(state) : state;
    });

    render(<App />);

    // Deve mostrar informações da faixa
    expect(screen.getByText('Test Song')).toBeInTheDocument();
    expect(screen.getByText('Test Artist')).toBeInTheDocument();
  });

  it('shows keyboard shortcuts hint in footer', () => {
    render(<App />);

    // Verifica dicas de atalhos de teclado
    expect(screen.getByText(/← → Adjust offset/)).toBeInTheDocument();
    expect(screen.getByText(/R Reset/)).toBeInTheDocument();
    expect(screen.getByText(/D Debug/)).toBeInTheDocument();
    expect(screen.getByText(/ESC Exit/)).toBeInTheDocument();
  });

  it('clears error after 5 seconds', async () => {
    vi.useFakeTimers();

    vi.mocked(useAppStore).mockImplementation((selector: any) => {
      const state = { ...mockStore, error: 'Test error' };
      if (selector === useAppStore.getState) {
        return { setError: mockStore.setError };
      }
      return selector ? selector(state) : state;
    });

    render(<App />);

    // Verifica que o erro está sendo exibido
    expect(screen.getByText('Test error')).toBeInTheDocument();

    // Avança o timer em 5 segundos
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    // Verifica que setError foi chamado com null
    expect(mockStore.setError).toHaveBeenCalledWith(null);

    vi.useRealTimers();
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

  it('applies correct CSS classes for connection status', () => {
    const mockTrack = {
      id: 'test-track-id',
      name: 'Test Song',
      artist: 'Test Artist',
      album: { name: 'Test Album', images: [] },
      duration_ms: 180000,
      is_playing: true,
    };

    // Teste desconectado
    vi.mocked(useAppStore).mockImplementation((selector: any) => {
      const state = { 
        ...mockStore, 
        currentTrack: mockTrack,
        isConnected: false, 
        syncState: { ...mockStore.syncState, global_offset: -100 } 
      };
      if (selector === useAppStore.getState) {
        return { setError: mockStore.setError };
      }
      return selector ? selector(state) : state;
    });

    const { rerender } = render(<App />);

    // Verifica ícone de desconectado
    let wifiOffIcon = document.querySelector('.lucide-wifi-off');
    expect(wifiOffIcon).toBeInTheDocument();
    
    // Verifica badge de offset negativo
    let offsetBadge = document.querySelector('.bg-red-500\\/20');
    expect(offsetBadge).toBeInTheDocument();

    // Teste conectado
    vi.mocked(useAppStore).mockImplementation((selector: any) => {
      const state = { 
        ...mockStore, 
        currentTrack: mockTrack,
        isConnected: true, 
        syncState: { ...mockStore.syncState, global_offset: 100 } 
      };
      if (selector === useAppStore.getState) {
        return { setError: mockStore.setError };
      }
      return selector ? selector(state) : state;
    });

    rerender(<App />);

    // Verifica ícone de conectado
    let wifiIcon = document.querySelector('.lucide-wifi');
    expect(wifiIcon).toBeInTheDocument();
    
    // Verifica badge de offset positivo
    offsetBadge = document.querySelector('.bg-green-500\\/20');
    expect(offsetBadge).toBeInTheDocument();
  });
});
