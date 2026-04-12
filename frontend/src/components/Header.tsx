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
      <header className="bg-app-surface border-b border-app-border px-6 py-3 flex items-center justify-end flex-shrink-0">
        <button
          onClick={() => setSearchOpen(true)}
          className="flex items-center gap-2 bg-app-surface-2 border border-app-border rounded-lg px-3 py-1.5 text-xs text-slate-500 hover:text-slate-300 hover:border-accent/30 transition-colors"
        >
          <span>⌕</span>
          <span>Search all messages</span>
          <kbd className="text-[10px] border border-app-border rounded px-1 py-0.5 ml-1">⌘K</kbd>
        </button>
      </header>
      <GlobalSearch open={searchOpen} onClose={() => setSearchOpen(false)} />
    </>
  )
}
