import { execSync } from 'node:child_process'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite rejects unknown Host headers (DNS-rebinding guard). `just run-dev` serves on the Tailscale IP,
// so allow this machine's MagicDNS names: the full `<host>.<tailnet>.ts.net` and its short form.
function tailscaleHosts(): string[] {
  try {
    const status = JSON.parse(execSync('tailscale status --self --json', { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }))
    const fqdn = String(status.Self?.DNSName ?? '').replace(/\.$/, '')
    return fqdn ? [fqdn, fqdn.split('.')[0]] : []
  } catch {
    return []  // no Tailscale: localhost-only dev needs nothing extra
  }
}

export default defineConfig({
  plugins: [react()],
  server: {
    // Same port as the production server (`just run`), so the URL is identical in dev and prod.
    port: 8050,
    strictPort: true,
    // `home-wsl` is hardcoded too, so it works even when the tailscale CLI lookup fails.
    allowedHosts: ['home-wsl', ...tailscaleHosts()],
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
