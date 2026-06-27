import { useMemo, useState } from 'react'
import { useQueries, useQuery } from '@tanstack/react-query'
import { api, SemanticUnavailableError } from '../api/client'
import type { MessagesMetadata } from '../api/types'
import { CardSpinner } from '../components/Spinner'
import DatetimeInput, { DATETIME_RE, formatDatetime, toApiDatetime } from '../components/DatetimeInput'
import SearchableChipFilter from '../components/messages/SearchableChipFilter'
import MessagesCard from '../components/messages/MessagesCard'
import ExportButton from '../components/ExportButton'
import { useDebounce } from '../hooks/useDebounce'
import { formatDateTime } from '../utils/datetime'
import type { SemanticSearchHit } from '../api/types'

// ── constants ─────────────────────────────────────────────────────────────────

const PAGE_SIZE = 100

type Preset = '7d' | '30d' | '90d' | '1y' | 'all'
type SearchMode = 'keyword' | 'semantic'

const PRESETS: { label: string; value: Preset }[] = [
  { label: '7d', value: '7d' },
  { label: '30d', value: '30d' },
  { label: '3m', value: '90d' },
  { label: '1y', value: '1y' },
  { label: 'All', value: 'all' },
]

// ── helpers ───────────────────────────────────────────────────────────────────

function presetDates(preset: Exclude<Preset, 'all'>): { from: string; to: string } {
  const days = { '7d': 7, '30d': 30, '90d': 90, '1y': 365 }[preset]
  const from = new Date()
  from.setDate(from.getDate() - days)
  from.setHours(0, 0, 0, 0)
  return { from: formatDatetime(from), to: '' }
}

function floorToHour(ms: number): string {
  const d = new Date(ms)
  d.setMinutes(0, 0, 0)
  return formatDatetime(d)
}

function ceilToHour(ms: number): string {
  const d = new Date(ms)
  if (d.getMinutes() !== 0 || d.getSeconds() !== 0 || d.getMilliseconds() !== 0) {
    d.setHours(d.getHours() + 1)
  }
  d.setMinutes(0, 0, 0)
  return formatDatetime(d)
}

// ── semantic results ──────────────────────────────────────────────────────────

function SemanticHitCard({ hit }: { hit: SemanticSearchHit }) {
  const [expanded, setExpanded] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['semantic-hit', hit.chat_id, hit.timestamp_start, hit.timestamp_end],
    queryFn: () =>
      api.chatMessages(
        hit.chat_id,
        200,
        0,
        hit.timestamp_start,
        hit.timestamp_end,
      ),
    enabled: expanded,
  })

  return (
    <div className="bg-app-surface border border-app-border rounded-xl overflow-hidden">
      <button
        className="w-full px-4 py-3 flex items-center gap-3 text-left hover:bg-app-surface-2 transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <span className="text-tx-muted text-xs">{expanded ? '▾' : '▸'}</span>
        <div className="flex-1 min-w-0">
          <span className="font-medium text-sm text-tx-primary truncate block">{hit.chat_name}</span>
          <span className="text-xs text-tx-muted">
            {formatDateTime(hit.timestamp_start)} – {formatDateTime(hit.timestamp_end)}
          </span>
          {!expanded && hit.text && (
            <span className="text-xs text-tx-secondary mt-1 line-clamp-3 whitespace-pre-line">{hit.text}</span>
          )}
        </div>
        <span
          className="text-[11px] px-1.5 py-0.5 rounded bg-accent/10 text-accent-light font-mono"
          title="Relevance score"
        >
          {(hit.score * 100).toFixed(0)}%
        </span>
      </button>

      {expanded && (
        <div className="border-t border-app-border p-4">
          {isLoading ? (
            <CardSpinner className="h-24" />
          ) : !data || data.messages.length === 0 ? (
            <p className="text-xs text-tx-muted text-center py-4">No messages found in this window</p>
          ) : (
            <MessagesCard
              messages={[...data.messages].reverse()}
              total={data.total}
              showChat={false}
              dayOnly={false}
              height="320px"
            />
          )}
        </div>
      )}
    </div>
  )
}

// ── main page ─────────────────────────────────────────────────────────────────

export default function GlobalMessagesPage() {
  const [searchMode, setSearchMode] = useState<SearchMode>('keyword')

  // keyword mode state
  const [dateFrom, setDateFrom] = useState(() => presetDates('30d').from)
  const [dateTo, setDateTo] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [activeChats, setActiveChats] = useState<Set<number>>(new Set())
  const [activeSenders, setActiveSenders] = useState<Set<string>>(new Set())
  const [offset, setOffset] = useState(0)
  const searchTerm = useDebounce(searchInput, 300)

  // semantic mode state
  const [semanticInput, setSemanticInput] = useState('')
  const [semanticQuery, setSemanticQuery] = useState('')

  const fromValid = !dateFrom || DATETIME_RE.test(dateFrom)
  const toValid = !dateTo || DATETIME_RE.test(dateTo)
  const rangeInvalid = !!(dateFrom && dateTo && fromValid && toValid && dateTo < dateFrom)

  const apiDateFrom = dateFrom && fromValid ? toApiDatetime(dateFrom) : undefined
  const apiDateTo = dateTo && toValid ? toApiDatetime(dateTo) : undefined
  const { data: bounds } = useQuery({
    queryKey: ['messages-bounds'],
    queryFn: () => api.messageBounds(),
    staleTime: Infinity,
  })

  const filterReady = searchMode === 'keyword' && !rangeInvalid && fromValid && toValid && !!dateFrom

  const sortedChatIds = useMemo(() => [...activeChats].sort(), [activeChats])
  const sortedSenderIds = useMemo(() => [...activeSenders].sort(), [activeSenders])
  const chatIdsParam = activeChats.size > 0 ? [...activeChats] : undefined
  const senderIdsParam = activeSenders.size > 0 ? [...activeSenders] : undefined

  // Step 1: metadata — total count + available IDs (fast: COUNT + DISTINCT only)
  const { data: metadata, isLoading: isMetaLoading } = useQuery<MessagesMetadata>({
    queryKey: ['global-messages-metadata', apiDateFrom, apiDateTo, searchTerm, sortedChatIds, sortedSenderIds],
    queryFn: () => api.messagesMetadata(apiDateFrom, apiDateTo, searchTerm || undefined, chatIdsParam, senderIdsParam),
    enabled: filterReady,
  })

  // Step 2a: messages page (fires after metadata resolves, using same filters)
  const { data: messagesData, isLoading: isMessagesLoading } = useQuery({
    queryKey: ['global-messages', offset, apiDateFrom, apiDateTo, searchTerm, sortedChatIds, sortedSenderIds],
    queryFn: () =>
      api.globalMessages(PAGE_SIZE, offset, apiDateFrom, apiDateTo, searchTerm || undefined, chatIdsParam, senderIdsParam),
    enabled: !!metadata,
  })

  // Step 2b: all chats — fires after metadata resolves
  const { data: chats = [], isLoading: isChatsLoading } = useQuery({
    queryKey: ['chats'],
    queryFn: () => api.chats(),
    enabled: !!metadata,
  })

  // Step 2c: sender names — batched at 100 IDs per request to avoid 431 errors
  const availableSenderIds = useMemo(
    () => metadata?.available_sender_ids ?? [],
    [metadata],
  )
  const senderIdBatches = useMemo(() => {
    const batches: string[][] = []
    for (let i = 0; i < availableSenderIds.length; i += 100) {
      batches.push(availableSenderIds.slice(i, i + 100))
    }
    return batches
  }, [availableSenderIds])

  const senderBatchResults = useQueries({
    queries: senderIdBatches.map((batch) => ({
      queryKey: ['senders', batch],
      queryFn: () => api.senders(batch),
      enabled: batch.length > 0,
    })),
  })
  const isSendersLoading = senderBatchResults.some((r) => r.isLoading)
  const senders = useMemo(
    () => senderBatchResults.flatMap((r) => r.data ?? []),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [senderBatchResults.map((r) => r.dataUpdatedAt).join(',')],
  )

  // semantic query
  const {
    data: semanticHits,
    isLoading: isSemanticLoading,
    error: semanticError,
  } = useQuery({
    queryKey: ['semantic-search', semanticQuery],
    queryFn: () => api.semanticSearch(semanticQuery),
    enabled: searchMode === 'semantic' && semanticQuery.length >= 2,
    retry: false,
  })

  const isUnavailable = semanticError instanceof SemanticUnavailableError

  const availableChatIds = useMemo(
    () => metadata?.available_chat_ids ? new Set(metadata.available_chat_ids) : null,
    [metadata],
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
    () => senders.map((s) => ({ id: s.sender_id, label: s.sender_name, searchText: `${s.sender_name} ${s.phone}` })),
    [senders],
  )

  const total = metadata?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE)

  function reset() { setOffset(0) }

  function applyPreset(p: Preset) {
    if (p === 'all') {
      setDateFrom(bounds?.first_ts ? floorToHour(bounds.first_ts) : '')
      setDateTo(bounds?.last_ts ? ceilToHour(bounds.last_ts) : '')
    } else {
      const { from, to } = presetDates(p)
      setDateFrom(from)
      setDateTo(to)
    }
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
  const btnClass = "px-2 py-1 rounded bg-app-surface-2 border border-app-border disabled:opacity-30 hover:text-tx-primary transition-colors"

  const pagination = totalPages > 1 ? (
    <div className="flex items-center gap-1 text-xs text-tx-secondary">
      <button onClick={() => setOffset(lastOffset)} disabled={offset >= lastOffset} className={btnClass} title="Oldest">«</button>
      <button onClick={() => setOffset(Math.min(lastOffset, offset + 10 * PAGE_SIZE))} disabled={offset >= lastOffset} className={btnClass} title="+10 pages">‹‹</button>
      <button onClick={() => setOffset(Math.min(lastOffset, offset + PAGE_SIZE))} disabled={offset >= lastOffset} className={btnClass}>‹ Older</button>
      <span className="tabular-nums px-1">{totalPages - currentPage} / {totalPages}</span>
      <button onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} disabled={offset === 0} className={btnClass}>Newer ›</button>
      <button onClick={() => setOffset(Math.max(0, offset - 10 * PAGE_SIZE))} disabled={offset === 0} className={btnClass} title="−10 pages">››</button>
      <button onClick={() => setOffset(0)} disabled={offset === 0} className={btnClass} title="Newest">»</button>
    </div>
  ) : null

  return (
    <div className="max-w-5xl space-y-4">
      <div>
        <h2 className="text-xl font-bold text-tx-primary">Messages</h2>
        <p className="text-xs text-tx-muted mt-1">Search and browse all messages across all chats</p>
      </div>

      {/* Mode toggle */}
      <div className="flex gap-1 bg-app-surface border border-app-border rounded-lg p-1 w-fit">
        {(['keyword', 'semantic'] as SearchMode[]).map((mode) => (
          <button
            key={mode}
            onClick={() => setSearchMode(mode)}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors capitalize ${
              searchMode === mode
                ? 'bg-accent/20 text-accent-light border border-accent/30'
                : 'text-tx-muted hover:text-tx-primary'
            }`}
          >
            {mode}
          </button>
        ))}
      </div>

      {searchMode === 'keyword' ? (
        <>
          {/* Keyword filter bar */}
          <div className="bg-app-surface border border-app-border rounded-xl p-4">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-xs font-semibold text-tx-secondary uppercase tracking-widest flex-shrink-0">Filter</span>

              <div className="relative flex-shrink-0">
                <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-tx-muted text-xs pointer-events-none">⌕</span>
                <input
                  type="text"
                  placeholder="Search messages…"
                  value={searchInput}
                  onChange={(e) => { setSearchInput(e.target.value); reset() }}
                  className="bg-app-surface-2 border border-app-border rounded-lg pl-7 pr-7 py-1.5 text-xs text-tx-secondary placeholder-tx-muted focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 w-44"
                />
                {searchInput && (
                  <button
                    onClick={() => setSearchInput('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-tx-muted hover:text-tx-secondary text-xs"
                  >✕</button>
                )}
              </div>

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

              <div className="flex gap-1">
                {PRESETS.map((p) => {
                  const active = p.value === 'all'
                    ? (bounds?.first_ts ? dateFrom === floorToHour(bounds.first_ts) : !dateFrom)
                    : presetDates(p.value).from.slice(0, 10) === dateFrom.slice(0, 10) && !dateTo
                  return (
                    <button
                      key={p.value}
                      onClick={() => applyPreset(p.value)}
                      className={`px-2 py-1 rounded text-[11px] font-medium transition-colors border ${active
                        ? 'bg-accent/15 border-accent/50 text-accent-light'
                        : 'bg-app-surface-2 border-app-border text-tx-muted hover:text-tx-primary'
                        }`}
                    >
                      {p.label}
                    </button>
                  )
                })}
              </div>

              <div className="ml-auto">
                <ExportButton
                  total={total}
                  filename="messages"
                  disabled={!metadata || total === 0 || rangeInvalid || !fromValid || !toValid}
                  onFetchPage={(limit, offset) =>
                    api.globalMessages(
                      limit,
                      offset,
                      apiDateFrom,
                      apiDateTo,
                      searchTerm || undefined,
                      activeChats.size > 0 ? [...activeChats] : undefined,
                      activeSenders.size > 0 ? [...activeSenders] : undefined,
                      'asc',
                    )
                  }
                />
              </div>
            </div>
          </div>

          <div className="flex gap-4 items-start">
            <div className="flex-1 min-w-0">
              <SearchableChipFilter
                title={`Chats (${isChatsLoading || isMetaLoading ? '…' : chatItems.length})`}
                items={chatItems}
                activeIds={activeChatIds}
                onToggle={toggleChat}
                onClear={() => { setActiveChats(new Set()); reset() }}
                isLoading={isChatsLoading || isMetaLoading}
              />
            </div>
            <div className="flex-1 min-w-0">
              <SearchableChipFilter
                title={`Senders (${isSendersLoading || isMetaLoading ? '…' : senderItems.length})`}
                items={senderItems}
                activeIds={activeSenders}
                onToggle={toggleSender}
                onClear={() => { setActiveSenders(new Set()); reset() }}
                isLoading={isSendersLoading || isMetaLoading}
              />
            </div>
          </div>

          {isMetaLoading || isMessagesLoading ? (
            <div className="bg-app-surface border border-app-border rounded-xl">
              <CardSpinner className="h-64" />
            </div>
          ) : !metadata || total === 0 ? (
            <div className="bg-app-surface border border-app-border rounded-xl p-8 text-center text-tx-muted text-sm">
              {filterReady
                ? (searchTerm ? `No messages matching "${searchTerm}"` : 'No messages in this range')
                : 'Select a date range to browse messages'}
            </div>
          ) : (
            <MessagesCard
              messages={messagesData ? [...messagesData.messages].reverse() : []}
              total={total}
              showChat
              dayOnly={false}
              height="calc(100vh - 420px)"
              highlight={searchTerm}
              header={pagination}
              onChatClick={toggleChat}
              onSenderClick={toggleSender}
            />
          )}
        </>
      ) : (
        <>
          {/* Semantic search bar */}
          <div className="bg-app-surface border border-app-border rounded-xl p-4">
            <form
              className="flex gap-2"
              onSubmit={(e) => {
                e.preventDefault()
                setSemanticQuery(semanticInput.trim())
              }}
            >
              <div className="relative flex-1">
                <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-tx-muted text-xs pointer-events-none">⌕</span>
                <input
                  type="text"
                  placeholder="Search by meaning… (supports Hebrew & English)"
                  value={semanticInput}
                  onChange={(e) => setSemanticInput(e.target.value)}
                  className="w-full bg-app-surface-2 border border-app-border rounded-lg pl-7 pr-3 py-1.5 text-xs text-tx-secondary placeholder-tx-muted focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20"
                />
              </div>
              <button
                type="submit"
                disabled={semanticInput.trim().length < 2}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-accent/20 text-accent-light border border-accent/30 disabled:opacity-40 hover:bg-accent/30 transition-colors"
              >
                Search
              </button>
            </form>

            <div className="mt-3 text-[11px] leading-relaxed text-tx-muted space-y-1">
              <p className="font-medium text-tx-secondary">How to search</p>
              <p>
                Describe <span className="text-tx-secondary">what was said</span>, not how you'd ask it. A short phrase
                works better than a single word, and you don't need a question — searching for the topic or a
                paraphrase of the actual message is best.
              </p>
              <p>
                If you remember any <span className="text-tx-secondary">distinctive words, names, or places</span> from
                the conversation, include them — exact terms sharpen the match on top of the meaning-based search.
              </p>
              <p>
                Results are whole <span className="text-tx-secondary">conversation windows</span> ranked by relevance,
                not single messages — click one to read the surrounding chat.
              </p>
            </div>
          </div>

          {isUnavailable ? (
            <div className="bg-app-surface border border-app-border rounded-xl p-6 text-center space-y-1">
              <p className="text-sm text-tx-primary font-medium">Semantic search index not built</p>
              <p className="text-xs text-tx-muted font-mono">just index --msgstore &lt;path&gt;</p>
            </div>
          ) : isSemanticLoading ? (
            <div className="bg-app-surface border border-app-border rounded-xl">
              <CardSpinner className="h-48" />
            </div>
          ) : semanticQuery && semanticHits?.length === 0 ? (
            <div className="bg-app-surface border border-app-border rounded-xl p-8 text-center text-tx-muted text-sm">
              No matching conversations found
            </div>
          ) : semanticHits && semanticHits.length > 0 ? (
            <div className="space-y-3">
              <p className="text-xs text-tx-muted">{semanticHits.length} conversation windows — click to expand</p>
              {semanticHits.map((hit) => (
                <SemanticHitCard key={`${hit.chat_id}-${hit.timestamp_start}`} hit={hit} />
              ))}
            </div>
          ) : null}
        </>
      )}
    </div>
  )
}
