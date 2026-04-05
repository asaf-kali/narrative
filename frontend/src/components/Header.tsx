import { useEffect, useState } from 'react'
import GlobalSearch from './GlobalSearch'

export default function Header() {
  const [searchOpen, setSearchOpen] = useState(false)

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
      <header className="bg-app-surface border-b border-app-border px-6 py-3 flex items-center justify-between flex-shrink-0">
        <h1 className="text-sm font-semibold text-slate-200 tracking-tight">WhatsApp Analyzer</h1>
        <button
          onClick={() => setSearchOpen(true)}
          className="flex items-center gap-2 bg-app-surface-2 border border-app-border rounded-lg px-3 py-1.5 text-xs text-slate-500 hover:text-slate-300 hover:border-accent/30 transition-colors"
        >
          <span>⌕</span>
          <span>Search all messages</span>
          <kbd className="text-[10px] border border-app-border rounded px-1 py-0.5 ml-1">⌘K</kbd>
        </button>
        <span className="text-[11px] text-app-muted">All processing is local — no data leaves your device</span>
      </header>
      <GlobalSearch open={searchOpen} onClose={() => setSearchOpen(false)} />
    </>
  )
}
