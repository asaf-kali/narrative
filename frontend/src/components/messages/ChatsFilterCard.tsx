import { useState } from 'react'

// ── helpers ───────────────────────────────────────────────────────────────────

function shortName(name: string, max = 20): string {
  return name.length > max ? name.slice(0, max - 1) + '…' : name
}

// ── component ─────────────────────────────────────────────────────────────────

interface Props {
  chatNames: string[]
  activeChats: Set<string>
  colorMap: Map<string, string>
  onToggle: (chat: string) => void
  onClear: () => void
}

/** Renders a searchable chat filter card with color-coded chips. Returns null if ≤1 chat. */
export default function ChatsFilterCard({ chatNames, activeChats, colorMap, onToggle, onClear }: Props) {
  const [query, setQuery] = useState('')

  if (chatNames.length <= 1) return null

  const lq = query.toLowerCase()
  const visible = lq ? chatNames.filter((c) => c.toLowerCase().includes(lq)) : chatNames

  return (
    <div className="bg-app-surface border border-app-border rounded-xl p-4 space-y-2.5">
      {/* Header row */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-tx-muted uppercase tracking-widest">Chats</span>
        {activeChats.size > 0 && (
          <button
            onClick={onClear}
            className="ml-auto text-[11px] text-tx-muted hover:text-tx-secondary transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* Search input */}
      <div className="relative">
        <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-tx-muted text-xs pointer-events-none">⌕</span>
        <input
          type="text"
          placeholder="Search chats…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full bg-app-surface-2 border border-app-border rounded-lg pl-7 pr-7 py-1.5 text-xs text-tx-secondary placeholder-tx-muted focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20"
        />
        {query && (
          <button
            onClick={() => setQuery('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-tx-muted hover:text-tx-secondary text-xs"
          >
            ✕
          </button>
        )}
      </div>

      {/* Chips */}
      <div className="flex flex-wrap gap-1.5">
        {visible.map((chat) => (
          <button
            key={chat}
            onClick={() => onToggle(chat)}
            className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors border truncate max-w-[160px] ${
              activeChats.has(chat)
                ? 'border-accent/50 text-accent-light'
                : 'bg-app-surface-2 border-app-border text-tx-secondary hover:text-tx-primary'
            }`}
            style={activeChats.has(chat) ? { backgroundColor: (colorMap.get(chat) ?? '#7c5af6') + '22' } : undefined}
            title={chat}
          >
            {shortName(chat)}
          </button>
        ))}
        {visible.length === 0 && (
          <span className="text-xs text-tx-muted">No matches for "{query}"</span>
        )}
      </div>
    </div>
  )
}
