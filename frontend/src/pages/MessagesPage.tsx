import { useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import MessageFeed from '../components/MessageFeed'
import { useDebounce } from '../hooks/useDebounce'

const PAGE_SIZE = 2000

type Preset = '7d' | '30d' | '90d' | '1y' | 'custom' | 'all'

const PRESETS: { label: string; value: Preset }[] = [
  { label: '7 days', value: '7d' },
  { label: '30 days', value: '30d' },
  { label: '3 months', value: '90d' },
  { label: '1 year', value: '1y' },
  { label: 'Custom', value: 'custom' },
  { label: 'All time', value: 'all' },
]

function presetToDates(preset: Preset): { dateFrom: string | undefined; dateTo: string | undefined } {
  if (preset === 'all' || preset === 'custom') return { dateFrom: undefined, dateTo: undefined }
  const days = { '7d': 7, '30d': 30, '90d': 90, '1y': 365 }[preset]
  const from = new Date()
  from.setDate(from.getDate() - days)
  return { dateFrom: from.toISOString().slice(0, 10), dateTo: undefined }
}

export default function MessagesPage() {
  const { chatId } = useParams<{ chatId: string }>()
  const [preset, setPreset] = useState<Preset>('30d')
  const [customFrom, setCustomFrom] = useState('')
  const [customTo, setCustomTo] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [offset, setOffset] = useState(0)

  const searchTerm = useDebounce(searchInput, 300)

  const { dateFrom, dateTo } = useMemo(() => {
    if (preset === 'custom') return { dateFrom: customFrom || undefined, dateTo: customTo || undefined }
    return presetToDates(preset)
  }, [preset, customFrom, customTo])

  const { data, isLoading } = useQuery({
    queryKey: ['chat-messages', chatId, offset, dateFrom, dateTo, searchTerm],
    queryFn: () => api.chatMessages(Number(chatId), PAGE_SIZE, offset, dateFrom, dateTo, searchTerm || undefined),
    enabled: !!chatId,
  })

  const senders: string[] = useMemo(() => {
    if (!data) return []
    const freq = new Map<string, number>()
    for (const m of data.messages) freq.set(m.sender_name, (freq.get(m.sender_name) ?? 0) + 1)
    return [...freq.entries()].sort((a, b) => b[1] - a[1]).map(([s]) => s)
  }, [data])

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0
  const currentPage = Math.floor(offset / PAGE_SIZE)

  function handlePreset(p: Preset) { setPreset(p); setOffset(0) }
  function handleCustomDate() { setOffset(0) }

  return (
    <div className="bg-app-surface border border-app-border rounded-xl p-4 space-y-3">
      {/* Controls row */}
      <div className="flex flex-wrap items-center gap-3">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest flex-shrink-0">
          Message History
        </h3>

        {/* Search input */}
        <div className="relative flex-shrink-0">
          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 text-xs pointer-events-none">⌕</span>
          <input
            type="text"
            placeholder="Search messages…"
            value={searchInput}
            onChange={(e) => { setSearchInput(e.target.value); setOffset(0) }}
            className="bg-app-surface-2 border border-app-border rounded-lg pl-7 pr-3 py-1.5 text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 w-48"
          />
          {searchInput && (
            <button
              onClick={() => setSearchInput('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-xs"
            >
              ✕
            </button>
          )}
        </div>

        {/* Preset chips */}
        <div className="flex gap-1.5 flex-wrap">
          {PRESETS.map((p) => (
            <button
              key={p.value}
              onClick={() => handlePreset(p.value)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors border ${
                preset === p.value
                  ? 'bg-accent/15 border-accent/50 text-accent-light'
                  : 'bg-app-surface-2 border-app-border text-slate-400 hover:text-slate-200'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Custom date inputs */}
        {preset === 'custom' && (
          <div className="flex items-center gap-2 text-xs">
            <input
              type="date"
              value={customFrom}
              onChange={(e) => { setCustomFrom(e.target.value); handleCustomDate() }}
              className="bg-app-surface-2 border border-app-border rounded px-2 py-1 text-slate-300 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20"
            />
            <span className="text-slate-500">→</span>
            <input
              type="date"
              value={customTo}
              onChange={(e) => { setCustomTo(e.target.value); handleCustomDate() }}
              className="bg-app-surface-2 border border-app-border rounded px-2 py-1 text-slate-300 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20"
            />
          </div>
        )}

        {/* Pagination — pushed to the right */}
        {totalPages > 1 && (
          <div className="ml-auto flex items-center gap-2 text-xs text-slate-400">
            <button
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              disabled={offset === 0}
              className="px-2 py-1 rounded bg-app-surface-2 border border-app-border disabled:opacity-30 hover:text-slate-200 transition-colors"
            >
              ← Older
            </button>
            <span className="tabular-nums">{currentPage + 1} / {totalPages}</span>
            <button
              onClick={() => setOffset(offset + PAGE_SIZE)}
              disabled={offset + PAGE_SIZE >= (data?.total ?? 0)}
              className="px-2 py-1 rounded bg-app-surface-2 border border-app-border disabled:opacity-30 hover:text-slate-200 transition-colors"
            >
              Newer →
            </button>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="h-64 bg-app-surface-2 rounded animate-pulse" />
      ) : !data || data.total === 0 ? (
        <div className="py-12 text-center text-slate-500 text-sm">
          {searchTerm ? `No messages matching "${searchTerm}"` : 'No messages in this range'}
        </div>
      ) : (
        <MessageFeed
          messages={data.messages}
          total={data.total}
          senders={senders}
          showChat={false}
          dayOnly={false}
          height="calc(100vh - 310px)"
          highlight={searchTerm}
        />
      )}
    </div>
  )
}
