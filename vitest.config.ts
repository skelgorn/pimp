import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
    exclude: [
      'e2e/**',
      'node_modules/**'
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test-setup.ts',
        '**/*.test.{ts,tsx}',
        '**/*.config.{ts,js}',
        'src-tauri/',
        'dist/',
        'coverage/',
        'e2e/'
      ]
    }
  }
});
