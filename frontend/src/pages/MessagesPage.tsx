import { useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { CardSpinner } from '../components/Spinner'
import DatetimeInput, { DATETIME_RE, formatDatetime, toApiDatetime } from '../components/DatetimeInput'
import SenderFilterCard from '../components/messages/SenderFilterCard'
import MessagesCard from '../components/messages/MessagesCard'
import { useDebounce } from '../hooks/useDebounce'

// ── constants ─────────────────────────────────────────────────────────────────

const PAGE_SIZE = 2000

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

export default function MessagesPage() {
  const { chatId } = useParams<{ chatId: string }>()
  const [dateFrom, setDateFrom] = useState(() => presetDates('30d').from)
  const [dateTo, setDateTo] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [offset, setOffset] = useState(0)
  // Single-select sender (server-side filter): at most one active at a time
  const [activeSenders, setActiveSenders] = useState<Set<string>>(new Set())

  const searchTerm = useDebounce(searchInput, 300)

  const fromValid = !dateFrom || DATETIME_RE.test(dateFrom)
  const toValid = !dateTo || DATETIME_RE.test(dateTo)
  const rangeInvalid = !!(dateFrom && dateTo && fromValid && toValid && dateTo < dateFrom)

  const { data: participants = [], isLoading: isParticipantsLoading } = useQuery({
    queryKey: ['participants', chatId],
    queryFn: () => api.participants(Number(chatId)),
    enabled: !!chatId,
  })

  // Map sender name → sender_id for server-side filter param
  const senderNameToId = useMemo(
    () => new Map(participants.map((p) => [p.sender_name, p.sender_id])),
    [participants],
  )

  const senderId = activeSenders.size > 0
    ? (senderNameToId.get([...activeSenders][0]) ?? '')
    : ''

  const senderNames = useMemo(() => participants.map((p) => p.sender_name), [participants])

  const { data, isLoading } = useQuery({
    queryKey: ['chat-messages', chatId, offset, dateFrom, dateTo, searchTerm, senderId],
    queryFn: () =>
      api.chatMessages(
        Number(chatId),
        PAGE_SIZE,
        offset,
        dateFrom && fromValid ? toApiDatetime(dateFrom) : undefined,
        dateTo && toValid ? toApiDatetime(dateTo) : undefined,
        searchTerm || undefined,
        senderId || undefined,
      ),
    enabled: !!chatId && !rangeInvalid && fromValid && toValid,
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

  // Single-select toggle: clicking an active sender deselects; clicking inactive clears others and selects
  function toggleSender(name: string) {
    setActiveSenders((prev) => {
      const next = new Set<string>()
      if (!prev.has(name)) next.add(name)
      return next
    })
    reset()
  }

  const pagination = totalPages > 1 ? (
    <div className="ml-auto flex items-center gap-2 text-xs text-tx-secondary">
      <button
        onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
        disabled={offset === 0}
        className="px-2 py-1 rounded bg-app-surface-2 border border-app-border disabled:opacity-30 hover:text-tx-primary transition-colors"
      >
        ← Older
      </button>
      <span className="tabular-nums">{currentPage + 1} / {totalPages}</span>
      <button
        onClick={() => setOffset(offset + PAGE_SIZE)}
        disabled={offset + PAGE_SIZE >= (data?.total ?? 0)}
        className="px-2 py-1 rounded bg-app-surface-2 border border-app-border disabled:opacity-30 hover:text-tx-primary transition-colors"
      >
        Newer →
      </button>
    </div>
  ) : null

  return (
    <div className="space-y-4">

      {/* Range card */}
      <div className="bg-app-surface border border-app-border rounded-xl p-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-xs font-semibold text-tx-secondary uppercase tracking-widest flex-shrink-0">Range</span>

          {/* Search */}
          <div className="relative flex-shrink-0">
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-tx-muted text-xs pointer-events-none">⌕</span>
            <input
              type="text"
              placeholder="Search…"
              value={searchInput}
              onChange={(e) => { setSearchInput(e.target.value); reset() }}
              className="bg-app-surface-2 border border-app-border rounded-lg pl-7 pr-7 py-1.5 text-xs text-tx-secondary placeholder-tx-muted focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 w-40"
            />
            {searchInput && (
              <button
                onClick={() => setSearchInput('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-tx-muted hover:text-tx-secondary text-xs"
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
            <span className={rangeInvalid ? 'text-red-400' : 'text-tx-muted'}>→</span>
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
              const active = from.slice(0, 10) === dateFrom.slice(0, 10) && (p.value === 'all' ? !dateTo : !dateTo || true)
              return (
                <button
                  key={p.value}
                  onClick={() => applyPreset(p.value)}
                  className={`px-2 py-1 rounded text-[11px] font-medium transition-colors border ${
                    active
                      ? 'bg-accent/15 border-accent/50 text-accent-light'
                      : 'bg-app-surface-2 border-app-border text-tx-muted hover:text-tx-primary'
                  }`}
                >
                  {p.label}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Sender filter card */}
      <SenderFilterCard
        senders={senderNames}
        activeSenders={activeSenders}
        onToggle={toggleSender}
        onClear={() => { setActiveSenders(new Set()); reset() }}
        isLoading={isParticipantsLoading}
      />

      {/* Messages card */}
      {isLoading ? (
        <div className="bg-app-surface border border-app-border rounded-xl">
          <CardSpinner className="h-64" />
        </div>
      ) : !data || data.total === 0 ? (
        <div className="bg-app-surface border border-app-border rounded-xl p-8 text-center text-tx-muted text-sm">
          {searchTerm ? `No messages matching "${searchTerm}"` : 'No messages in this range'}
        </div>
      ) : (
        <MessagesCard
          messages={data.messages}
          total={data.total}
          showChat={false}
          dayOnly={false}
          height="calc(100vh - 340px)"
          highlight={searchTerm}
          header={pagination}
        />
      )}
    </div>
  )
}
