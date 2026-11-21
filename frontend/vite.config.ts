import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // Same port as the production server (`just run`), so the URL is identical in dev and prod.
    port: 8050,
    strictPort: true,
    proxy: {
      // Dev backend port — keep in sync with DEV_BACKEND_PORT in the justfile.
      '/api': 'http://localhost:8051',
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-query': ['@tanstack/react-query'],
          'vendor-charts': ['recharts'],
          'vendor-graph': ['react-force-graph-2d'],
        },
      },
    },
  },
})
