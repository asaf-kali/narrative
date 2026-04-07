import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { DayMessage, FeedMessage } from '../api/types'
import { buildChatColorMap } from './MessageFeed'
import ActivityCard, { buildTimelineRows } from './messages/ActivityCard'
import ChatsFilterCard from './messages/ChatsFilterCard'
import SenderFilterCard from './messages/SenderFilterCard'
import MessagesCard from './messages/MessagesCard'

// ── constants ─────────────────────────────────────────────────────────────────

const MAX_LABELED_CHATS = 7

// ── helpers ───────────────────────────────────────────────────────────────────

function nextDay(date: string): string {
  const d = new Date(date + 'T00:00:00')
  d.setDate(d.getDate() + 1)
  return d.toISOString().slice(0, 10)
}

function dayMessageToFeed(msg: DayMessage): FeedMessage {
  // DayDetail messages have "HH:MM" time; synthesize a full timestamp with dummy date
  // so MessageFeed's dayOnly=true mode can slice the time back out
  return {
    timestamp: '1970-01-01T' + msg.time + ':00',
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

// ── main component ────────────────────────────────────────────────────────────

interface Props {
  date: string
  onClose: () => void
}

export default function DayDetail({ date, onClose }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ['day', date],
    queryFn: () => api.dayDetail(date),
  })

  const [activeChats, setActiveChats] = useState<Set<string>>(new Set())
  const [activeSenders, setActiveSenders] = useState<Set<string>>(new Set())

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

  const allChatNames: string[] = useMemo(() => {
    if (!data) return []
    const freq = new Map<string, number>()
    for (const b of data.timeline) freq.set(b.chat_name, (freq.get(b.chat_name) ?? 0) + b.count)
    return [...freq.entries()].sort((a, b) => b[1] - a[1]).map(([c]) => c)
  }, [data])

  const feedMessages: FeedMessage[] = useMemo(
    () => (data?.messages ?? []).map(dayMessageToFeed),
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
    <div className="bg-app-surface border border-accent/25 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-app-border">
        <div className="flex items-center gap-4">
          <span className="text-sm font-semibold text-slate-200">{date}</span>
          {data && (
            <>
              <StatPill label="messages" value={data.total_messages} />
              <StatPill label="chats" value={data.active_chats} />
            </>
          )}
        </div>
        <div className="flex items-center gap-3">
          <a
            href={`/messages?from=${encodeURIComponent(date + ' 00:00')}&to=${encodeURIComponent(nextDay(date) + ' 00:00')}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-slate-500 hover:text-accent-light transition-colors"
            title="Open in new window"
          >
            ↗ Open
          </a>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-300 transition-colors text-lg leading-none"
          >
            ✕
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="p-5 space-y-3 animate-pulse">
          <div className="h-40 bg-app-surface-2 rounded-xl" />
          <div className="h-12 bg-app-surface-2 rounded-xl" />
          <div className="h-64 bg-app-surface-2 rounded-xl" />
        </div>
      ) : !data || data.total_messages === 0 ? (
        <div className="p-8 text-center text-slate-500 text-sm">No messages on this day</div>
      ) : (
        <div className="p-5 space-y-4">
          {/* Activity graph card */}
          <ActivityCard
            rows={timelineRows}
            barKeys={barKeys}
            colorMap={colorMap}
            label="Activity (5-min buckets)"
            height={140}
            tickFormatter={(v: string) => v.slice(0, 2) + 'h'}
            tickInterval={11}
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
            dayOnly
            height="20rem"
          />
        </div>
      )}
    </div>
  )
}
