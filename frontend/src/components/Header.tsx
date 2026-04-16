import { useEffect, useState } from 'react'
import GlobalSearch from './GlobalSearch'
import { useTheme } from '../context/ThemeContext'

function SunIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <circle cx="12" cy="12" r="5"/>
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
  )
}

export default function Header() {
  const [searchOpen, setSearchOpen] = useState(false)
  const { theme, toggle } = useTheme()

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setSearchOpen((v) => !v)
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  return (
    <>
      <header className="bg-app-surface border-b border-app-border px-6 py-3 flex items-center justify-end gap-3 flex-shrink-0">
        <button
          onClick={() => setSearchOpen(true)}
          className="flex items-center gap-2 bg-app-surface-2 border border-app-border rounded-lg px-3 py-1.5 text-xs text-tx-muted hover:text-tx-secondary hover:border-accent/30 transition-colors"
        >
          <span>⌕</span>
          <span>Search all messages</span>
          <kbd className="text-[10px] border border-app-border rounded px-1 py-0.5 ml-1">⌘K</kbd>
        </button>
        <button
          onClick={toggle}
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          className="p-1.5 rounded-lg text-tx-muted hover:text-tx-secondary hover:bg-app-surface-2 border border-app-border transition-colors"
        >
          {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
        </button>
      </header>
      <GlobalSearch open={searchOpen} onClose={() => setSearchOpen(false)} />
    </>
  )
}
