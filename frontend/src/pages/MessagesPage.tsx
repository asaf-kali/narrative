import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import MessageFeed from '../components/MessageFeed'
import { useDebounce } from '../hooks/useDebounce'

const PAGE_SIZE = 2000

type Preset = '7d' | '30d' | '90d' | '1y' | 'all'

const PRESETS: { label: string; value: Preset }[] = [
  { label: '7d', value: '7d' },
  { label: '30d', value: '30d' },
  { label: '3m', value: '90d' },
  { label: '1y', value: '1y' },
  { label: 'All', value: 'all' },
]

function presetDates(preset: Preset): { from: string; to: string } {
  if (preset === 'all') return { from: '', to: '' }
  const days = { '7d': 7, '30d': 30, '90d': 90, '1y': 365 }[preset]
  const from = new Date()
  from.setDate(from.getDate() - days)
  return { from: from.toISOString().slice(0, 10), to: '' }
}

export default function MessagesPage() {
  const { chatId } = useParams<{ chatId: string }>()
  const [dateFrom, setDateFrom] = useState(() => presetDates('30d').from)
  const [dateTo, setDateTo] = useState('')
  const [senderId, setSenderId] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [offset, setOffset] = useState(0)

  const searchTerm = useDebounce(searchInput, 300)

  // Load participants for the sender dropdown (no date filter — show all senders ever)
  const { data: participants = [] } = useQuery({
    queryKey: ['participants', chatId],
    queryFn: () => api.participants(Number(chatId)),
    enabled: !!chatId,
  })

  const { data, isLoading } = useQuery({
    queryKey: ['chat-messages', chatId, offset, dateFrom, dateTo, searchTerm, senderId],
    queryFn: () =>
      api.chatMessages(
        Number(chatId),
        PAGE_SIZE,
        offset,
        dateFrom || undefined,
        dateTo || undefined,
        searchTerm || undefined,
        senderId || undefined,
      ),
    enabled: !!chatId,
  })

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0
  const currentPage = Math.floor(offset / PAGE_SIZE)

  function applyPreset(p: Preset) {
    const { from, to } = presetDates(p)
    setDateFrom(from)
    setDateTo(to)
    setOffset(0)
  }

  function reset() { setOffset(0) }

  return (
    <div className="bg-app-surface border border-app-border rounded-xl p-4 space-y-3">

      {/* ── Row 1: search + date range ── */}
      <div className="flex flex-wrap items-center gap-3">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest flex-shrink-0">
          Message History
        </h3>

        {/* Search */}
        <div className="relative flex-shrink-0">
          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 text-xs pointer-events-none">⌕</span>
          <input
            type="text"
            placeholder="Search…"
            value={searchInput}
            onChange={(e) => { setSearchInput(e.target.value); reset() }}
            className="bg-app-surface-2 border border-app-border rounded-lg pl-7 pr-7 py-1.5 text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 w-40"
          />
          {searchInput && (
            <button onClick={() => setSearchInput('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-xs">✕</button>
          )}
        </div>

        {/* Date range */}
        <div className="flex items-center gap-2 text-xs">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); reset() }}
            className="bg-app-surface-2 border border-app-border rounded px-2 py-1.5 text-slate-300 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20"
          />
          <span className="text-slate-500">→</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); reset() }}
            className="bg-app-surface-2 border border-app-border rounded px-2 py-1.5 text-slate-300 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20"
          />
        </div>

        {/* Preset shortcuts */}
        <div className="flex gap-1">
          {PRESETS.map((p) => {
            const { from } = presetDates(p.value)
            const active = from === dateFrom && (p.value === 'all' ? !dateTo : true)
            return (
              <button
                key={p.value}
                onClick={() => applyPreset(p.value)}
                className={`px-2 py-1 rounded text-[11px] font-medium transition-colors border ${
                  active
                    ? 'bg-accent/15 border-accent/50 text-accent-light'
                    : 'bg-app-surface-2 border-app-border text-slate-500 hover:text-slate-200'
                }`}
              >
                {p.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* ── Row 2: sender + pagination ── */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Sender dropdown */}
        {participants.length > 1 && (
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500">Sender</span>
            <select
              value={senderId}
              onChange={(e) => { setSenderId(e.target.value); reset() }}
              className="bg-app-surface-2 border border-app-border rounded px-2 py-1.5 text-slate-300 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 text-xs"
            >
              <option value="">All senders</option>
              {participants.map((p) => (
                <option key={p.sender_id} value={p.sender_id}>
                  {p.sender_name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Pagination */}
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

      {/* ── Feed ── */}
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
          senders={[]}
          showChat={false}
          dayOnly={false}
          height="calc(100vh - 340px)"
          highlight={searchTerm}
        />
      )}
    </div>
  )
}
