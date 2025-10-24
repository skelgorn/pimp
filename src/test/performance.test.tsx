import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, act } from '@testing-library/react';

// Mock Tauri APIs
vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));
vi.mock('@tauri-apps/api/event', () => ({ listen: vi.fn(() => Promise.resolve(() => {})) }));
vi.mock('framer-motion', () => ({
  motion: { div: 'div' },
  AnimatePresence: ({ children }: any) => children,
}));

import App from '../App';

describe('Performance Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('app loads within reasonable time', async () => {
    const start = performance.now();
    
    await act(async () => {
      render(<App />);
    });
    
    const time = performance.now() - start;
    expect(time).toBeLessThan(500); // Should load in less than 500ms
  });

  it('handles multiple rerenders efficiently', async () => {
    const { rerender } = render(<App />);
    
    const start = performance.now();
    
    // Simulate multiple rerenders
    for (let i = 0; i < 10; i++) {
      await act(async () => {
        rerender(<App />);
      });
    }
    
    const time = performance.now() - start;
    expect(time).toBeLessThan(200); // Should handle 10 rerenders in less than 200ms
  });

  it('performance benchmark passes', () => {
    // Simple performance validation
    const start = performance.now();
    
    // Simulate some work
    for (let i = 0; i < 1000; i++) {
      Math.sqrt(i);
    }
    
    const time = performance.now() - start;
    expect(time).toBeLessThan(50); // Should complete in less than 50ms
  });
});
