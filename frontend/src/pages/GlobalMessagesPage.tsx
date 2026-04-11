import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import DatetimeInput, { DATETIME_RE, formatDatetime, toApiDatetime } from '../components/DatetimeInput'
import SearchableChipFilter from '../components/messages/SearchableChipFilter'
import MessagesCard from '../components/messages/MessagesCard'
import { useDebounce } from '../hooks/useDebounce'

// ── constants ─────────────────────────────────────────────────────────────────

const PAGE_SIZE = 100

type Preset = '7d' | '30d' | '90d' | '1y' | 'all'

const PRESETS: { label: string; value: Preset }[] = [
  { label: '7d', value: '7d' },
  { label: '30d', value: '30d' },
  { label: '3m', value: '90d' },
  { label: '1y', value: '1y' },
  { label: 'All', value: 'all' },
]

// ── helpers ───────────────────────────────────────────────────────────────────

function presetDates(preset: Preset): { from: string; to: string } {
  if (preset === 'all') return { from: '', to: '' }
  const days = { '7d': 7, '30d': 30, '90d': 90, '1y': 365 }[preset]
  const from = new Date()
  from.setDate(from.getDate() - days)
  from.setHours(0, 0, 0, 0)
  return { from: formatDatetime(from), to: '' }
}

// ── main page ─────────────────────────────────────────────────────────────────

export default function GlobalMessagesPage() {
  const [dateFrom, setDateFrom] = useState(() => presetDates('30d').from)
  const [dateTo, setDateTo] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [activeChats, setActiveChats] = useState<Set<number>>(new Set())
  const [activeSenders, setActiveSenders] = useState<Set<string>>(new Set())
  const [offset, setOffset] = useState(0)

  const searchTerm = useDebounce(searchInput, 300)

  const fromValid = !dateFrom || DATETIME_RE.test(dateFrom)
  const toValid = !dateTo || DATETIME_RE.test(dateTo)
  const rangeInvalid = !!(dateFrom && dateTo && fromValid && toValid && dateTo < dateFrom)

  const { data: chats = [] } = useQuery({ queryKey: ['chats'], queryFn: api.chats })
  const { data: senders = [] } = useQuery({ queryKey: ['senders'], queryFn: api.senders })

  const { data, isLoading } = useQuery({
    queryKey: ['global-messages', offset, dateFrom, dateTo, searchTerm, [...activeChats].sort(), [...activeSenders].sort()],
    queryFn: () =>
      api.globalMessages(
        PAGE_SIZE,
        offset,
        dateFrom && fromValid ? toApiDatetime(dateFrom) : undefined,
        dateTo && toValid ? toApiDatetime(dateTo) : undefined,
        searchTerm || undefined,
        activeChats.size > 0 ? [...activeChats] : undefined,
        activeSenders.size > 0 ? [...activeSenders] : undefined,
      ),
    enabled: !rangeInvalid && fromValid && toValid,
  })

  const availableChatIds = useMemo(
    () => data?.available_chat_ids ? new Set(data.available_chat_ids) : null,
    [data],
  )
  const availableSenderIds = useMemo(
    () => data?.available_sender_ids ? new Set(data.available_sender_ids) : null,
    [data],
  )

  const chatItems = useMemo(
    () =>
      chats
        .filter((c) => !availableChatIds || availableChatIds.has(c.chat_id))
        .sort((a, b) => b.message_count - a.message_count)
        .map((c) => ({ id: String(c.chat_id), label: c.display_name, searchText: c.display_name })),
    [chats, availableChatIds],
  )

  const senderItems = useMemo(
    () =>
      senders
        .filter((s) => !availableSenderIds || availableSenderIds.has(s.sender_id))
        .map((s) => ({ id: s.sender_id, label: s.sender_name, searchText: `${s.sender_name} ${s.phone}` })),
    [senders, availableSenderIds],
  )

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0
  const currentPage = Math.floor(offset / PAGE_SIZE)

  function reset() {
    setOffset(0)
  }

  function applyPreset(p: Preset) {
    const { from, to } = presetDates(p)
    setDateFrom(from)
    setDateTo(to)
    reset()
  }

  function toggleChat(id: string) {
    setActiveChats((prev) => {
      const next = new Set(prev)
      const numId = Number(id)
      if (next.has(numId)) next.delete(numId)
      else next.add(numId)
      return next
    })
    reset()
  }

  function toggleSender(id: string) {
    setActiveSenders((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
    reset()
  }

  const activeChatIds = useMemo(() => new Set([...activeChats].map(String)), [activeChats])

  const lastOffset = (totalPages - 1) * PAGE_SIZE
  const btnClass = "px-2 py-1 rounded bg-app-surface-2 border border-app-border disabled:opacity-30 hover:text-slate-200 transition-colors"

  const pagination = totalPages > 1 ? (
    <div className="flex items-center gap-1 text-xs text-slate-400">
      {/* jump to oldest */}
      <button onClick={() => setOffset(lastOffset)} disabled={offset >= lastOffset} className={btnClass} title="Oldest">«</button>
      {/* +10 pages (older) */}
      <button onClick={() => setOffset(Math.min(lastOffset, offset + 10 * PAGE_SIZE))} disabled={offset >= lastOffset} className={btnClass} title="+10 pages">‹‹</button>
      {/* +1 page (older) */}
      <button onClick={() => setOffset(Math.min(lastOffset, offset + PAGE_SIZE))} disabled={offset >= lastOffset} className={btnClass}>‹ Older</button>

      <span className="tabular-nums px-1">{totalPages - currentPage} / {totalPages}</span>

      {/* −1 page (newer) */}
      <button onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} disabled={offset === 0} className={btnClass}>Newer ›</button>
      {/* −10 pages (newer) */}
      <button onClick={() => setOffset(Math.max(0, offset - 10 * PAGE_SIZE))} disabled={offset === 0} className={btnClass} title="−10 pages">››</button>
      {/* jump to newest */}
      <button onClick={() => setOffset(0)} disabled={offset === 0} className={btnClass} title="Newest">»</button>
    </div>
  ) : null

  return (
    <div className="max-w-5xl space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-100">Messages</h2>
        <p className="text-xs text-slate-500 mt-1">Search and browse all messages across all chats</p>
      </div>

      {/* Filter bar */}
      <div className="bg-app-surface border border-app-border rounded-xl p-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest flex-shrink-0">Filter</span>

          {/* Content search */}
          <div className="relative flex-shrink-0">
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 text-xs pointer-events-none">⌕</span>
            <input
              type="text"
              placeholder="Search messages…"
              value={searchInput}
              onChange={(e) => { setSearchInput(e.target.value); reset() }}
              className="bg-app-surface-2 border border-app-border rounded-lg pl-7 pr-7 py-1.5 text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 w-44"
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

          {/* Date range */}
          <div className="flex items-center gap-2 text-xs">
            <DatetimeInput
              value={dateFrom}
              onChange={(v) => { setDateFrom(v); reset() }}
              isInvalid={(!!dateFrom && !fromValid) || rangeInvalid}
            />
            <span className={rangeInvalid ? 'text-red-400' : 'text-slate-500'}>→</span>
            <DatetimeInput
              value={dateTo}
              onChange={(v) => { setDateTo(v); reset() }}
              isInvalid={(!!dateTo && !toValid) || rangeInvalid}
            />
            {(rangeInvalid || (dateFrom && !fromValid) || (dateTo && !toValid)) && (
              <span className="text-red-400 text-[11px]">
                {rangeInvalid ? 'End must be after start' : 'Use yyyy-mm-dd HH:MM'}
              </span>
            )}
          </div>

          {/* Preset shortcuts */}
          <div className="flex gap-1">
            {PRESETS.map((p) => {
              const { from } = presetDates(p.value)
              const active = p.value === 'all'
                ? (!dateFrom && !dateTo)
                : from.slice(0, 10) === dateFrom.slice(0, 10) && !dateTo
              return (
                <button
                  key={p.value}
                  onClick={() => applyPreset(p.value)}
                  className={`px-2 py-1 rounded text-[11px] font-medium transition-colors border ${active
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
      </div>

      {/* Chats + Senders side by side */}
      <div className="flex gap-4 items-start">
        <div className="flex-1 min-w-0">
          <SearchableChipFilter
            title={`Chats (${chatItems.length})`}
            items={chatItems}
            activeIds={activeChatIds}
            onToggle={toggleChat}
            onClear={() => { setActiveChats(new Set()); reset() }}
          />
        </div>
        <div className="flex-1 min-w-0">
          <SearchableChipFilter
            title={`Senders (${senderItems.length})`}
            items={senderItems}
            activeIds={activeSenders}
            onToggle={toggleSender}
            onClear={() => { setActiveSenders(new Set()); reset() }}
          />
        </div>
      </div>

      {/* Messages feed */}
      {isLoading ? (
        <div className="bg-app-surface border border-app-border rounded-xl h-64 animate-pulse" />
      ) : !data || data.total === 0 ? (
        <div className="bg-app-surface border border-app-border rounded-xl p-8 text-center text-slate-500 text-sm">
          {searchTerm ? `No messages matching "${searchTerm}"` : 'No messages in this range'}
        </div>
      ) : (
        <MessagesCard
          messages={[...data.messages].reverse()}
          total={data.total}
          showChat
          dayOnly={false}
          height="calc(100vh - 420px)"
          highlight={searchTerm}
          header={pagination}
          onChatClick={toggleChat}
          onSenderClick={toggleSender}
        />
      )}
    </div>
  )
}
