import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CardSpinner } from '../Spinner'
import { useDebounce } from '../../hooks/useDebounce'

// ── types ─────────────────────────────────────────────────────────────────────

export interface ChipItem {
  id: string
  label: string
  /** Text used for search matching — may include phone, aliases, etc. */
  searchText: string
}

export interface RemoteChipResult {
  items: ChipItem[]
  total: number
}

interface Props {
  title: string
  items: ChipItem[]
  /** Count of every available item. When given, it is shown in the title; when larger than
   *  `items.length`, every search also queries `remoteSearch` for matches beyond `items`. */
  total?: number
  remoteSearch?: (query: string) => Promise<RemoteChipResult>
  /** Cache key for remote results — must change whenever `remoteSearch`'s scope changes. */
  remoteKey?: readonly unknown[]
  activeIds: Set<string>
  onToggle: (id: string) => void
  onClear: () => void
  isLoading?: boolean
}

// ── helpers ───────────────────────────────────────────────────────────────────

const COUNT_CAP = 100
const REMOTE_DEBOUNCE_MS = 300

function formatCount(n: number): string {
  return n > COUNT_CAP ? `${COUNT_CAP}+` : String(n)
}

function activeFirst(items: ChipItem[], activeIds: Set<string>): ChipItem[] {
  return [...items.filter((i) => activeIds.has(i.id)), ...items.filter((i) => !activeIds.has(i.id))]
}

// ── component ─────────────────────────────────────────────────────────────────

/** Chip filter card with a built-in search input. Returns null if ≤1 item and not loading. */
export default function SearchableChipFilter({
  title, items, total, remoteSearch, remoteKey = [], activeIds, onToggle, onClear, isLoading,
}: Props) {
  const [query, setQuery] = useState('')
  // Every chip the user toggled, so active chips stay visible after they leave `items`
  // (e.g. picked from remote results, or dropped by a date-range change).
  const [picked, setPicked] = useState<Map<string, ChipItem>>(new Map())
  const debouncedQuery = useDebounce(query.trim(), REMOTE_DEBOUNCE_MS)

  const lq = query.trim().toLowerCase()
  const localMatches = lq ? items.filter((item) => item.searchText.toLowerCase().includes(lq)) : items
  const available = total ?? items.length
  // Local matches show instantly; the backend is still asked, since `items` is only the top slice.
  const useRemote = !!remoteSearch && !!lq && available > items.length
  const debounceSettled = debouncedQuery.toLowerCase() === lq

  const remote = useQuery({
    queryKey: ['chip-remote-search', ...remoteKey, debouncedQuery.toLowerCase()],
    queryFn: () => remoteSearch!(debouncedQuery),
    enabled: useRemote && debounceSettled,
  })
  const isRemoteLoading = useRemote && (!debounceSettled || remote.isFetching)

  if (isLoading) {
    return (
      <div className="bg-app-surface border border-app-border rounded-xl p-4">
        <span className="text-[10px] text-tx-muted uppercase tracking-widest">{title}</span>
        <CardSpinner className="h-12" />
      </div>
    )
  }

  if (available <= 1 && activeIds.size === 0) return null

  const remoteData = useRemote && !isRemoteLoading ? remote.data : undefined
  const localIds = new Set(localMatches.map((i) => i.id))
  const remoteExtras = remoteData?.items.filter((i) => !localIds.has(i.id)) ?? []
  const matches = [...localMatches, ...remoteExtras]
  const matchCount = remoteData
    ? Math.max(remoteData.total, localMatches.length)
    : lq ? localMatches.length : available

  const known = new Map([...picked, ...items.map((i) => [i.id, i] as const)])
  const activeItems = [...activeIds].flatMap((id) => known.get(id) ?? [])
  const visible = lq
    ? activeFirst(matches, activeIds)
    : [...activeItems, ...items.filter((i) => !activeIds.has(i.id))]

  function toggle(item: ChipItem) {
    setPicked((prev) => new Map(prev).set(item.id, item))
    onToggle(item.id)
  }

  const countLabel = total === undefined ? '' : ` (${formatCount(matchCount)}${isRemoteLoading ? '…' : ''})`

  return (
    <div className="bg-app-surface border border-app-border rounded-xl p-4 space-y-2.5">
      {/* Header row */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-tx-muted uppercase tracking-widest">{title}{countLabel}</span>
        {activeIds.size > 0 && (
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
          placeholder={`Search ${title.toLowerCase()}…`}
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
      <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto">
        {visible.map((item) => (
          <button
            key={item.id}
            onClick={() => toggle(item)}
            title={item.label}
            className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors border truncate max-w-[200px] ${
              activeIds.has(item.id)
                ? 'bg-accent/15 border-accent/50 text-accent-light'
                : 'bg-app-surface-2 border-app-border text-tx-secondary hover:text-tx-primary'
            }`}
          >
            {item.label}
          </button>
        ))}
        {isRemoteLoading && (
          <span className="inline-flex items-center px-2 py-1" role="status" aria-label="Searching…">
            <span className="w-3 h-3 border-2 border-app-border border-t-accent rounded-full animate-spin" />
          </span>
        )}
        {!isRemoteLoading && visible.length === 0 && (
          <span className="text-xs text-tx-muted">
            {useRemote && remote.isError ? 'Search failed' : `No matches for "${query.trim()}"`}
          </span>
        )}
      </div>
    </div>
  )
}
