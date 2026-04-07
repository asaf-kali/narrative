import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { FeedMessage, RangeMessage } from '../api/types'
import { buildChatColorMap } from '../components/MessageFeed'
import DatetimeInput, { DATETIME_RE, toApiDatetime } from '../components/DatetimeInput'
import ActivityCard, { buildTimelineRows } from '../components/messages/ActivityCard'
import ChatsFilterCard from '../components/messages/ChatsFilterCard'
import SenderFilterCard from '../components/messages/SenderFilterCard'
import MessagesCard from '../components/messages/MessagesCard'

// ── constants ─────────────────────────────────────────────────────────────────

const MAX_LABELED_CHATS = 7
const DAY_MS = 86_400_000

// ── helpers ───────────────────────────────────────────────────────────────────

/** Format bucket label ("YYYY-MM-DDTHH:MM") based on bucket size in ms. */
function formatTick(bucketSizeMs: number): (v: string) => string {
  if (bucketSizeMs < DAY_MS)         return (v) => v.slice(11, 16)  // "HH:MM"
  if (bucketSizeMs < DAY_MS * 30)    return (v) => v.slice(5, 10)   // "MM-DD"
  if (bucketSizeMs < DAY_MS * 365)   return (v) => v.slice(0, 7)    // "YYYY-MM"
  return (v) => v.slice(0, 4)                                         // "YYYY"
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
  const [activeSenders, setActiveSenders] = useState<Set<string>>(new Set())

  const fromValid = DATETIME_RE.test(from)
  const toValid = DATETIME_RE.test(to)
  const rangeInvalid = fromValid && toValid && to < from
  const canFetch = fromValid && toValid && !rangeInvalid

  const bucketSizeMs = canFetch
    ? (new Date(to.replace(' ', 'T')).getTime() - new Date(from.replace(' ', 'T')).getTime()) / 30
    : DAY_MS

  const { data, isLoading } = useQuery({
    queryKey: ['range', from, to],
    queryFn: () => api.rangeDetail(toApiDatetime(from), toApiDatetime(to)),
    enabled: canFetch,
  })

  function handleChange(newFrom: string, newTo: string) {
    setSearchParams({ from: newFrom, to: newTo }, { replace: true })
    setActiveChats(new Set())
    setActiveSenders(new Set())
  }

  const topChats: string[] = useMemo(() => {
    if (!data) return []
    const freq = new Map<string, number>()
    for (const b of data.timeline) freq.set(b.chat_name, (freq.get(b.chat_name) ?? 0) + b.count)
    return [...freq.entries()].sort((a, b) => b[1] - a[1]).slice(0, MAX_LABELED_CHATS).map(([c]) => c)
  }, [data])

  const colorMap = useMemo(() => buildChatColorMap(topChats), [topChats])

  const timelineRows = useMemo(
    () => (data ? buildTimelineRows(data.timeline, topChats, data.buckets) : []),
    [data, topChats],
  )

  const barKeys: string[] = useMemo(() => {
    const hasOther = data?.timeline.some((b) => !topChats.includes(b.chat_name)) ?? false
    return [...topChats, ...(hasOther ? ['Other'] : [])]
  }, [topChats, data])

  const allChatNames: string[] = useMemo(() => {
    if (!data) return []
    const freq = new Map<string, number>()
    for (const b of data.timeline) freq.set(b.chat_name, (freq.get(b.chat_name) ?? 0) + b.count)
    return [...freq.entries()].sort((a, b) => b[1] - a[1]).map(([c]) => c)
  }, [data])

  const feedMessages: FeedMessage[] = useMemo(
    () => (data?.messages ?? []).map(rangeMessageToFeed),
    [data],
  )

  const visibleMessages = useMemo(() => {
    let msgs = feedMessages
    if (activeChats.size > 0) msgs = msgs.filter((m) => activeChats.has(m.chat_name))
    if (activeSenders.size > 0) msgs = msgs.filter((m) => activeSenders.has(m.sender_name))
    return msgs
  }, [feedMessages, activeChats, activeSenders])

  function toggleChat(chat: string) {
    setActiveChats((prev) => {
      const next = new Set(prev)
      if (next.has(chat)) next.delete(chat)
      else next.add(chat)
      return next
    })
  }

  function toggleSender(sender: string) {
    setActiveSenders((prev) => {
      const next = new Set(prev)
      if (next.has(sender)) next.delete(sender)
      else next.add(sender)
      return next
    })
  }

  return (
    <div className="max-w-5xl space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-100">Messages</h2>
        <p className="text-xs text-slate-500 mt-1">All messages across all chats in a time range</p>
      </div>

      {/* Range card */}
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
          <div className="bg-app-surface border border-app-border rounded-xl h-12" />
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
          {/* Activity graph card */}
          <ActivityCard
            rows={timelineRows}
            barKeys={barKeys}
            colorMap={colorMap}
            label="Activity (30 buckets)"
            tickFormatter={formatTick(bucketSizeMs)}
          />

          {/* Chats filter card */}
          <ChatsFilterCard
            chatNames={allChatNames}
            activeChats={activeChats}
            colorMap={colorMap}
            onToggle={toggleChat}
            onClear={() => setActiveChats(new Set())}
          />

          {/* Sender filter card */}
          <SenderFilterCard
            senders={data.senders}
            activeSenders={activeSenders}
            onToggle={toggleSender}
            onClear={() => setActiveSenders(new Set())}
          />

          {/* Messages card */}
          <MessagesCard
            messages={visibleMessages}
            total={visibleMessages.length}
            showChat
            dayOnly={false}
            height="calc(100vh - 420px)"
          />
        </>
      )}
    </div>
  )
}
