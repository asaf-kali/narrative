import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { api } from '../api/client'
import type { FeedMessage, RangeMessage } from '../api/types'
import MessageFeed, { buildChatColorMap, CHAT_COLORS } from '../components/MessageFeed'
import DatetimeInput, { DATETIME_RE, toApiDatetime } from '../components/DatetimeInput'

// ── constants ─────────────────────────────────────────────────────────────────

const MAX_LABELED_CHATS = 7
const OTHER_COLOR = '#374061'
const TOOLTIP_STYLE = { background: '#0d0f17', border: '1px solid #1a1d2e', color: '#e2e8f0', borderRadius: 8, fontSize: 12 }
const TICK_STYLE = { fill: '#64748b', fontSize: 10 }

// ── helpers ───────────────────────────────────────────────────────────────────

type Bucket = 'hourly' | 'daily' | 'weekly' | 'monthly' | 'yearly'

// Granularities ordered finest→coarsest, with their size in hours
const GRANULARITIES: { bucket: Bucket; hours: number }[] = [
  { bucket: 'hourly',  hours: 1 },
  { bucket: 'daily',   hours: 24 },
  { bucket: 'weekly',  hours: 24 * 7 },
  { bucket: 'monthly', hours: 24 * 30 },
  { bucket: 'yearly',  hours: 24 * 365 },
]

/** Pick the granularity whose bucket count is closest to TARGET_BUCKETS. */
function chooseBucket(from: string, to: string): Bucket {
  const TARGET = 30
  const rangeHours = (new Date(to.replace(' ', 'T')).getTime() - new Date(from.replace(' ', 'T')).getTime()) / 3_600_000
  return GRANULARITIES.reduce((best, g) => {
    const count = rangeHours / g.hours
    const bestCount = rangeHours / best.hours
    return Math.abs(count - TARGET) < Math.abs(bestCount - TARGET) ? g : best
  }).bucket
}

function formatTick(bucket: Bucket): (v: string) => string {
  if (bucket === 'hourly')  return (v) => v.slice(11, 16)  // "HH:00"
  if (bucket === 'daily')   return (v) => v.slice(5)        // "MM-DD"
  if (bucket === 'weekly')  return (v) => v.slice(5)        // "W##"
  if (bucket === 'monthly') return (v) => v                  // "YYYY-MM"
  return (v) => v                                             // "YYYY"
}

type TimelineRow = { bucket: string } & Record<string, number | string>

function buildTimelineRows(
  timeline: { bucket: string; chat_name: string; count: number }[],
  topChats: string[],
): TimelineRow[] {
  const topSet = new Set(topChats)
  const map = new Map<string, TimelineRow>()
  for (const b of timeline) {
    if (!map.has(b.bucket)) map.set(b.bucket, { bucket: b.bucket })
    const row = map.get(b.bucket)!
    const key = topSet.has(b.chat_name) ? b.chat_name : 'Other'
    row[key] = ((row[key] as number | undefined) ?? 0) + b.count
  }
  return [...map.values()]
}

function shortName(name: string, max = 22): string {
  return name.length > max ? name.slice(0, max - 1) + '…' : name
}

function rangeMessageToFeed(msg: RangeMessage): FeedMessage {
  return {
    timestamp: msg.timestamp + ':00',
    chat_name: msg.chat_name,
    sender_id: msg.sender_name,
    sender_name: msg.sender_name,
    text: msg.text,
    message_type: msg.message_type,
  }
}

// ── stat pill ─────────────────────────────────────────────────────────────────

function StatPill({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center gap-2 bg-app-surface-2 border border-app-border rounded-lg px-3 py-2">
      <span className="text-slate-500 text-xs">{label}</span>
      <span className="text-slate-200 text-sm font-semibold tabular-nums">
        {typeof value === 'number' ? value.toLocaleString() : value}
      </span>
    </div>
  )
}

// ── main page ─────────────────────────────────────────────────────────────────

export default function RangeDetailPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const from = searchParams.get('from') ?? ''
  const to = searchParams.get('to') ?? ''

  const [activeChats, setActiveChats] = useState<Set<string>>(new Set())

  const fromValid = DATETIME_RE.test(from)
  const toValid = DATETIME_RE.test(to)
  const rangeInvalid = fromValid && toValid && to < from
  const canFetch = fromValid && toValid && !rangeInvalid

  const bucket: Bucket = canFetch ? chooseBucket(from, to) : 'daily'

  const { data, isLoading } = useQuery({
    queryKey: ['range', from, to, bucket],
    queryFn: () => api.rangeDetail(toApiDatetime(from), toApiDatetime(to), bucket),
    enabled: canFetch,
  })

  function handleChange(newFrom: string, newTo: string) {
    setSearchParams({ from: newFrom, to: newTo }, { replace: true })
    setActiveChats(new Set())
  }

  const topChats: string[] = useMemo(() => {
    if (!data) return []
    const freq = new Map<string, number>()
    for (const b of data.timeline) freq.set(b.chat_name, (freq.get(b.chat_name) ?? 0) + b.count)
    return [...freq.entries()].sort((a, b) => b[1] - a[1]).slice(0, MAX_LABELED_CHATS).map(([c]) => c)
  }, [data])

  const colorMap = useMemo(() => buildChatColorMap(topChats), [topChats])

  const timelineRows = useMemo(
    () => (data ? buildTimelineRows(data.timeline, topChats) : []),
    [data, topChats],
  )

  const barKeys: string[] = useMemo(() => {
    const hasOther = data?.timeline.some((b) => !topChats.includes(b.chat_name)) ?? false
    return [...topChats, ...(hasOther ? ['Other'] : [])]
  }, [topChats, data])

  const feedMessages: FeedMessage[] = useMemo(
    () => (data?.messages ?? []).map(rangeMessageToFeed),
    [data],
  )

  const allChatNames: string[] = useMemo(() => {
    if (!data) return []
    const freq = new Map<string, number>()
    for (const b of data.timeline) freq.set(b.chat_name, (freq.get(b.chat_name) ?? 0) + b.count)
    return [...freq.entries()].sort((a, b) => b[1] - a[1]).map(([c]) => c)
  }, [data])

  const visibleMessages = useMemo(
    () => (activeChats.size === 0 ? feedMessages : feedMessages.filter((m) => activeChats.has(m.chat_name))),
    [feedMessages, activeChats],
  )

  function toggleChat(chat: string) {
    setActiveChats((prev) => {
      const next = new Set(prev)
      if (next.has(chat)) next.delete(chat)
      else next.add(chat)
      return next
    })
  }

  return (
    <div className="max-w-5xl space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-100">Messages</h2>
        <p className="text-xs text-slate-500 mt-1">All messages across all chats in a time range</p>
      </div>

      {/* Date pickers */}
      <div className="bg-app-surface border border-app-border rounded-xl p-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest flex-shrink-0">Range</span>
          <div className="flex items-center gap-2 text-xs">
            <DatetimeInput
              value={from}
              onChange={(v) => handleChange(v, to)}
              isInvalid={(!!from && !fromValid) || !!rangeInvalid}
            />
            <span className={rangeInvalid ? 'text-red-400' : 'text-slate-500'}>→</span>
            <DatetimeInput
              value={to}
              onChange={(v) => handleChange(from, v)}
              isInvalid={(!!to && !toValid) || !!rangeInvalid}
            />
            {rangeInvalid && <span className="text-red-400 text-[11px]">End must be after start</span>}
            {!canFetch && !rangeInvalid && (
              <span className="text-slate-500 text-[11px]">Enter a date range to load messages</span>
            )}
          </div>
          {data && (
            <div className="ml-auto flex gap-3">
              <StatPill label="messages" value={data.total_messages} />
              <StatPill label="chats" value={data.active_chats} />
            </div>
          )}
        </div>
      </div>

      {isLoading && (
        <div className="space-y-3 animate-pulse">
          <div className="bg-app-surface border border-app-border rounded-xl h-40" />
          <div className="bg-app-surface border border-app-border rounded-xl h-64" />
        </div>
      )}

      {data && data.total_messages === 0 && (
        <div className="bg-app-surface border border-app-border rounded-xl p-8 text-center text-slate-500 text-sm">
          No messages in this range
        </div>
      )}

      {data && data.total_messages > 0 && (
        <>
          {/* Activity chart */}
          <div className="bg-app-surface border border-app-border rounded-xl p-4">
            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-2">
              Activity ({bucket})
            </p>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={timelineRows} barCategoryGap="10%">
                <XAxis
                  dataKey="bucket"
                  tick={TICK_STYLE}
                  interval="preserveStartEnd"
                  tickFormatter={formatTick(bucket)}
                />
                <YAxis tick={TICK_STYLE} width={28} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} formatter={(v: string) => shortName(v)} />
                {barKeys.map((key, i) => (
                  <Bar
                    key={key}
                    dataKey={key}
                    stackId="a"
                    fill={key === 'Other' ? OTHER_COLOR : (colorMap.get(key) ?? CHAT_COLORS[i % CHAT_COLORS.length])}
                    isAnimationActive={false}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Chat filter chips */}
          {allChatNames.length > 1 && (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] text-slate-500 uppercase tracking-widest flex-shrink-0">Chats</span>
              {allChatNames.map((chat) => (
                <button
                  key={chat}
                  onClick={() => toggleChat(chat)}
                  className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors border truncate max-w-[160px] ${
                    activeChats.has(chat)
                      ? 'border-accent/50 text-accent-light'
                      : 'bg-app-surface-2 border-app-border text-slate-400 hover:text-slate-200'
                  }`}
                  style={activeChats.has(chat) ? { backgroundColor: (colorMap.get(chat) ?? '#7c5af6') + '22' } : undefined}
                  title={chat}
                >
                  {shortName(chat, 20)}
                </button>
              ))}
              {activeChats.size > 0 && (
                <button
                  onClick={() => setActiveChats(new Set())}
                  className="px-2 py-1 text-[11px] text-slate-500 hover:text-slate-300 transition-colors"
                >
                  Clear
                </button>
              )}
            </div>
          )}

          {/* Message feed */}
          <div className="bg-app-surface border border-app-border rounded-xl overflow-hidden">
            <MessageFeed
              messages={visibleMessages}
              total={visibleMessages.length}
              senders={data.senders}
              showChat
              dayOnly={false}
              height="calc(100vh - 420px)"
            />
          </div>
        </>
      )}
    </div>
  )
}
