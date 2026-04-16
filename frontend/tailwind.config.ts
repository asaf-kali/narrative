import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        app: {
          bg: 'var(--app-bg)',
          surface: 'var(--app-surface)',
          'surface-2': 'var(--app-surface-2)',
          sidebar: 'var(--app-sidebar)',
          border: 'var(--app-border)',
          muted: 'var(--app-muted)',
          hover: 'var(--app-hover)',
        },
        tx: {
          primary: 'var(--tx-primary)',
          secondary: 'var(--tx-secondary)',
          muted: 'var(--tx-muted)',
          faint: 'var(--tx-faint)',
        },
        accent: {
          DEFAULT: '#7c5af6',
          light: '#a78bfa',
          dark: '#5b21b6',
        },
      },
    },
  },
  plugins: [],
} satisfies Config
