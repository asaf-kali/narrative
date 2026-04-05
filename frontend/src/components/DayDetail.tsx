import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { api } from '../api/client'
import type { DayMessage, FeedMessage } from '../api/types'
import MessageFeed, { buildChatColorMap, CHAT_COLORS } from './MessageFeed'

// ── constants ─────────────────────────────────────────────────────────────────

const MAX_LABELED_CHATS = 7
const OTHER_COLOR = '#374061'
const TOOLTIP_STYLE = { background: '#0d0f17', border: '1px solid #1a1d2e', color: '#e2e8f0', borderRadius: 8, fontSize: 12 }
const TICK_STYLE = { fill: '#64748b', fontSize: 10 }

// ── helpers ───────────────────────────────────────────────────────────────────

type TimelineRow = { bucket: string } & Record<string, number | string>

function buildTimelineRows(
  timeline: { bucket: string; chat_name: string; count: number }[],
  topChats: string[]
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

function dayMessageToFeed(msg: DayMessage): FeedMessage {
  // DayDetail messages have "HH:MM" time; synthesize a full timestamp with dummy date
  // so MessageFeed's dayOnly=true mode can slice the time back out
  return {
    timestamp: '1970-01-01T' + msg.time + ':00',
    chat_name: msg.chat_name,
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

  const topChats: string[] = useMemo(() => {
    if (!data) return []
    const freq = new Map<string, number>()
    for (const b of data.timeline) freq.set(b.chat_name, (freq.get(b.chat_name) ?? 0) + b.count)
    return [...freq.entries()].sort((a, b) => b[1] - a[1]).slice(0, MAX_LABELED_CHATS).map(([c]) => c)
  }, [data])

  const colorMap = useMemo(() => buildChatColorMap(topChats), [topChats])

  const timelineRows = useMemo(
    () => (data ? buildTimelineRows(data.timeline, topChats) : []),
    [data, topChats]
  )

  const barKeys: string[] = useMemo(() => {
    const hasOther = data?.timeline.some((b) => !topChats.includes(b.chat_name)) ?? false
    return [...topChats, ...(hasOther ? ['Other'] : [])]
  }, [topChats, data])

  const feedMessages: FeedMessage[] = useMemo(
    () => (data?.messages ?? []).map(dayMessageToFeed),
    [data]
  )

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
        <button
          onClick={onClose}
          className="text-slate-500 hover:text-slate-300 transition-colors text-lg leading-none"
        >
          ✕
        </button>
      </div>

      {isLoading ? (
        <div className="p-5 space-y-3 animate-pulse">
          <div className="h-32 bg-app-surface-2 rounded" />
          <div className="h-64 bg-app-surface-2 rounded" />
        </div>
      ) : !data || data.total_messages === 0 ? (
        <div className="p-8 text-center text-slate-500 text-sm">No messages on this day</div>
      ) : (
        <div className="p-5 space-y-4">
          {/* Activity chart */}
          <div>
            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-2">
              Activity (5-min buckets)
            </p>
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={timelineRows} barCategoryGap="10%">
                <XAxis
                  dataKey="bucket"
                  tick={TICK_STYLE}
                  interval={11}
                  tickFormatter={(v: string) => v.slice(0, 2) + 'h'}
                />
                <YAxis tick={TICK_STYLE} width={28} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Legend
                  wrapperStyle={{ fontSize: 11, color: '#94a3b8' }}
                  formatter={(v: string) => shortName(v)}
                />
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

          {/* Message feed */}
          <MessageFeed
            messages={feedMessages}
            total={data.total_messages}
            senders={data.senders}
            showChat
            dayOnly
            height="20rem"
          />
        </div>
      )}
    </div>
  )
}
