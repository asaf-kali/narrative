import { useState } from 'react'
import { CardSpinner } from '../Spinner'

// ── types ─────────────────────────────────────────────────────────────────────

export interface ChipItem {
  id: string
  label: string
  /** Text used for search matching — may include phone, aliases, etc. */
  searchText: string
}

interface Props {
  title: string
  items: ChipItem[]
  activeIds: Set<string>
  onToggle: (id: string) => void
  onClear: () => void
  isLoading?: boolean
}

// ── component ─────────────────────────────────────────────────────────────────

/** Chip filter card with a built-in search input. Returns null if ≤1 item and not loading. */
export default function SearchableChipFilter({ title, items, activeIds, onToggle, onClear, isLoading }: Props) {
  const [query, setQuery] = useState('')

  if (isLoading) {
    return (
      <div className="bg-app-surface border border-app-border rounded-xl p-4">
        <span className="text-[10px] text-slate-500 uppercase tracking-widest">{title}</span>
        <CardSpinner className="h-12" />
      </div>
    )
  }

  if (items.length <= 1) return null

  const lq = query.toLowerCase()
  const filtered = lq ? items.filter((item) => item.searchText.toLowerCase().includes(lq)) : items
  const visible = [
    ...filtered.filter((item) => activeIds.has(item.id)),
    ...filtered.filter((item) => !activeIds.has(item.id)),
  ]

  return (
    <div className="bg-app-surface border border-app-border rounded-xl p-4 space-y-2.5">
      {/* Header row */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-slate-500 uppercase tracking-widest">{title}</span>
        {activeIds.size > 0 && (
          <button
            onClick={onClear}
            className="ml-auto text-[11px] text-slate-500 hover:text-slate-300 transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* Search input */}
      <div className="relative">
        <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 text-xs pointer-events-none">⌕</span>
        <input
          type="text"
          placeholder={`Search ${title.toLowerCase()}…`}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full bg-app-surface-2 border border-app-border rounded-lg pl-7 pr-7 py-1.5 text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20"
        />
        {query && (
          <button
            onClick={() => setQuery('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-xs"
          >
            ✕
          </button>
        )}
      </div>

      {/* Chips */}
      <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto">
        {visible.map((item) => (
          <button
            key={item.id}
            onClick={() => onToggle(item.id)}
            title={item.label}
            className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors border truncate max-w-[200px] ${
              activeIds.has(item.id)
                ? 'bg-accent/15 border-accent/50 text-accent-light'
                : 'bg-app-surface-2 border-app-border text-slate-400 hover:text-slate-200'
            }`}
          >
            {item.label}
          </button>
        ))}
        {visible.length === 0 && (
          <span className="text-xs text-slate-600">No matches for "{query}"</span>
        )}
      </div>
    </div>
  )
}
