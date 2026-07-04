import { useMemo, useRef } from 'react'
import type { FeedMessage, MessageReactions, ReplyPreview } from '../api/types'
import { formatDate, formatDateTime } from '../utils/datetime'
import { CHAT_COLORS, Highlighted, quotedText } from './MessageFeed'

// ── helpers ───────────────────────────────────────────────────────────────────

/** Stable colour per participant id (deterministic hash → palette). */
function senderColor(id: string): string {
  let hash = 0
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) >>> 0
  return CHAT_COLORS[hash % CHAT_COLORS.length]
}

/** "HH:MM" from an ISO/naive timestamp string (local clock time). */
function clockTime(ts: string): string {
  return ts.slice(11, 16)
}

/** "YYYY-MM-DD" day key for separator grouping. */
function dayKey(ts: string): string {
  return ts.slice(0, 10)
}

// ── sub-components ────────────────────────────────────────────────────────────

function DaySeparator({ day }: { day: string }) {
  return (
    <div className="flex justify-center my-3">
      <span className="text-[10px] font-medium text-tx-muted bg-app-surface-2 rounded-full px-3 py-0.5">
        {formatDate(day)}
      </span>
    </div>
  )
}

function ReplyBox({ reply, color }: { reply: ReplyPreview; color: string }) {
  return (
    <div
      className="mb-1 rounded-md bg-black/10 dark:bg-black/20 border-l-2 pl-2 pr-2 py-1 min-w-0"
      style={{ borderColor: color }}
    >
      <div className="text-[11px] font-semibold truncate" style={{ color }}>
        {reply.sender_name}
      </div>
      <div className="text-[11px] text-tx-muted italic truncate">{quotedText(reply)}</div>
    </div>
  )
}

function Reactions({ reactions }: { reactions: MessageReactions }) {
  return (
    <div
      className="absolute -bottom-2.5 right-2 flex items-center gap-0.5"
      title={reactions.reactors.join(', ')}
    >
      {reactions.emojis.map((e, i) => (
        <span
          key={i}
          className="inline-flex items-center gap-0.5 text-[11px] bg-app-surface border border-app-border rounded-full px-1.5 py-0.5 leading-none shadow-sm"
        >
          <span>{e.emoji}</span>
          {e.count > 1 && <span className="tabular-nums text-tx-muted text-[9px]">{e.count}</span>}
        </span>
      ))}
    </div>
  )
}

interface BubbleProps {
  msg: FeedMessage
  showSender: boolean
  color: string
  highlight: string
}

function Bubble({ msg, showSender, color, highlight }: BubbleProps) {
  const isMe = msg.sender_id === 'me'
  const isMedia = msg.text?.startsWith('[') ?? false
  const hasReactions = !!msg.reactions && msg.reactions.total > 0

  const bubbleClass = isMe
    ? 'bg-emerald-600/25 dark:bg-emerald-500/20 border border-emerald-600/30'
    : 'bg-app-surface-2 border border-app-border'

  return (
    <div className={`flex ${isMe ? 'justify-end' : 'justify-start'} ${hasReactions ? 'mb-3' : ''}`}>
      <div className={`relative max-w-[75%] min-w-0 rounded-2xl px-3 py-1.5 ${bubbleClass}`}>
        {showSender && !isMe && (
          <div className="text-[11px] font-semibold mb-0.5 truncate" style={{ color }}>
            {msg.sender_name}
          </div>
        )}
        {msg.reply_to && <ReplyBox reply={msg.reply_to} color={color} />}
        <div className="flex flex-wrap items-end gap-x-2 min-w-0">
          <span
            className={`text-[13px] leading-snug break-words min-w-0 ${
              isMedia ? 'text-tx-muted italic' : 'text-tx-primary'
            }`}
          >
            {highlight && !isMedia ? <Highlighted text={msg.text ?? ''} term={highlight} /> : (msg.text ?? '')}
          </span>
          <span
            className="ml-auto text-[10px] text-tx-muted tabular-nums flex-shrink-0 cursor-default"
            title={formatDateTime(msg.timestamp)}
          >
            {clockTime(msg.timestamp)}
          </span>
        </div>
        {hasReactions && <Reactions reactions={msg.reactions!} />}
      </div>
    </div>
  )
}

// ── main component ────────────────────────────────────────────────────────────

interface Props {
  messages: FeedMessage[]
  total: number
  height?: string
  highlight?: string
}

export default function ChatBubbleFeed({ messages, total, height = '18rem', highlight = '' }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)

  // Show sender labels only in group chats (more than one non-me participant).
  const showSenders = useMemo(() => {
    const others = new Set(messages.filter((m) => m.sender_id !== 'me').map((m) => m.sender_id))
    return others.size > 1
  }, [messages])

  const colorMap = useMemo(() => {
    const map = new Map<string, string>()
    for (const m of messages) if (!map.has(m.sender_id)) map.set(m.sender_id, senderColor(m.sender_id))
    return map
  }, [messages])

  return (
    <div className="space-y-2">
      <p className="text-[10px] text-tx-muted">
        {messages.length < total
          ? `${messages.length.toLocaleString()} of ${total.toLocaleString()} messages`
          : `${messages.length.toLocaleString()} messages`}
      </p>

      <div
        ref={scrollRef}
        className="overflow-y-auto rounded-lg bg-app-bg border border-app-border px-3 py-2 space-y-1"
        style={{ height }}
      >
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-tx-muted text-sm">No messages</div>
        ) : (
          messages.map((msg, i) => {
            const prev = messages[i - 1]
            const newDay = !prev || dayKey(prev.timestamp) !== dayKey(msg.timestamp)
            return (
              <div key={i}>
                {newDay && <DaySeparator day={dayKey(msg.timestamp)} />}
                <Bubble
                  msg={msg}
                  showSender={showSenders}
                  color={colorMap.get(msg.sender_id) ?? CHAT_COLORS[0]}
                  highlight={highlight}
                />
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
