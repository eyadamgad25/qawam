import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

// QAWAM_BASE is the path the app is served under: "/" locally, "/qawam/" on
// GitHub Pages (set by .github/workflows/pages.yml). The model and WASM
// loaders read it through import.meta.env.BASE_URL.
export default defineConfig({
  base: process.env.QAWAM_BASE ?? '/',
  plugins: [react()],
  test: {
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
  },
});
