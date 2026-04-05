import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        app: {
          bg: '#07080d',
          surface: '#0d0f17',
          'surface-2': '#12151f',
          border: '#1a1d2e',
          muted: '#374061',
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
