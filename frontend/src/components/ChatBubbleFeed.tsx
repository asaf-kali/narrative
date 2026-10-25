import { useLayoutEffect, useMemo, useRef } from 'react'
import type { ContactCard, FeedMessage, MessageReactions, ReplyPreview } from '../api/types'
import { formatDate, formatExact } from '../utils/datetime'
import { CHAT_COLORS, Highlighted, quotedText } from './MessageFeed'

// ── constants ─────────────────────────────────────────────────────────────────

// Consecutive messages from the same sender within this gap form one visual group.
const GROUP_GAP_MS = 5 * 60 * 1000

const MEDIA_ICONS: Record<number, string> = {
  1: '📷', 2: '🎤', 3: '🎬', 4: '👤', 5: '📍', 9: '📄', 13: '🎞️', 14: '👥', 15: '🚫',
  16: '📡', 20: '🩹',
}

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

function tsMillis(ts: string): number {
  const parsed = Date.parse(ts)
  return Number.isNaN(parsed) ? 0 : parsed
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

function ReplyBox({ reply, color, onJump }: { reply: ReplyPreview; color: string; onJump: (id: number) => void }) {
  const jumpable = reply.quoted_message_id != null
  return (
    <button
      type="button"
      disabled={!jumpable}
      onClick={jumpable ? () => onJump(reply.quoted_message_id!) : undefined}
      title={jumpable ? 'Jump to quoted message' : undefined}
      className={`mb-1 w-full text-left rounded-md bg-black/10 dark:bg-black/20 border-l-2 pl-2 pr-2 py-1 min-w-0 ${
        jumpable ? 'cursor-pointer hover:bg-black/20 dark:hover:bg-black/30 transition-colors' : 'cursor-default'
      }`}
      style={{ borderColor: color }}
    >
      <div className="text-[11px] font-semibold truncate" style={{ color }}>
        {reply.sender_name}
      </div>
      <div className="text-[11px] text-tx-muted italic truncate">{quotedText(reply)}</div>
    </button>
  )
}

function Reactions({ reactions }: { reactions: MessageReactions }) {
  return (
    <div className="absolute -bottom-2.5 right-2 flex items-center gap-0.5" title={reactions.reactors.join(', ')}>
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

function ContactCards({ contacts }: { contacts: ContactCard[] }) {
  return (
    <div className="mt-1 flex flex-col gap-1">
      {contacts.map((c, i) => (
        <div key={i} className="rounded-lg bg-app-hover px-2 py-1 min-w-0">
          <div className="text-[12px] font-medium text-tx-primary truncate">{c.name}</div>
          {c.phones.map((p) => (
            <div key={p} className="text-[11px] text-tx-muted tabular-nums truncate">{p}</div>
          ))}
        </div>
      ))}
    </div>
  )
}

interface BubbleProps {
  msg: FeedMessage
  showName: boolean
  color: string
  highlight: string
  onJump: (id: number) => void
}

function Bubble({ msg, showName, color, highlight, onJump }: BubbleProps) {
  const isMe = msg.sender_id === 'me'
  const isMedia = msg.text?.startsWith('[') ?? false
  const hasReactions = !!msg.reactions && msg.reactions.total > 0
  const mediaIcon = isMedia ? MEDIA_ICONS[msg.message_type] : undefined

  const bubbleClass = isMe
    ? 'bg-emerald-600/25 dark:bg-emerald-500/20 border border-emerald-600/30'
    : 'bg-app-surface-2 border border-app-border'

  return (
    <div
      id={msg.message_id != null ? `msg-${msg.message_id}` : undefined}
      className={`flex ${isMe ? 'justify-end' : 'justify-start'} ${hasReactions ? 'mb-3' : ''} rounded-2xl transition-shadow`}
    >
      <div className={`relative max-w-[75%] min-w-0 rounded-2xl px-3 py-1.5 ${bubbleClass}`}>
        {showName && !isMe && (
          <div className="text-[11px] font-semibold mb-0.5 truncate" style={{ color }}>
            {msg.sender_name}
          </div>
        )}
        {msg.reply_to && <ReplyBox reply={msg.reply_to} color={color} onJump={onJump} />}
        <div className="flex flex-wrap items-end gap-x-2 min-w-0">
          <span
            className={`text-[13px] leading-snug break-words min-w-0 ${
              isMedia ? 'text-tx-muted italic' : 'text-tx-primary'
            }`}
          >
            {mediaIcon && <span className="mr-1 not-italic">{mediaIcon}</span>}
            {highlight && !isMedia ? <Highlighted text={msg.text ?? ''} term={highlight} /> : (msg.text ?? '')}
          </span>
          <span
            className="ml-auto text-[10px] text-tx-muted tabular-nums flex-shrink-0 cursor-default"
            title={formatExact(msg.timestamp)}
          >
            {clockTime(msg.timestamp)}
          </span>
        </div>
        {msg.contacts && msg.contacts.length > 0 && <ContactCards contacts={msg.contacts} />}
        {hasReactions && msg.reactions && <Reactions reactions={msg.reactions} />}
      </div>
    </div>
  )
}

// ── main component ────────────────────────────────────────────────────────────

interface RenderItem {
  msg: FeedMessage
  key: string
  newDay: boolean
  startOfGroup: boolean
}

function buildItems(messages: FeedMessage[]): RenderItem[] {
  return messages.map((msg, i) => {
    const prev = messages[i - 1]
    const newDay = !prev || dayKey(prev.timestamp) !== dayKey(msg.timestamp)
    const sameSender = !!prev && prev.sender_id === msg.sender_id
    const withinGap = !!prev && tsMillis(msg.timestamp) - tsMillis(prev.timestamp) < GROUP_GAP_MS
    const startOfGroup = newDay || !sameSender || !withinGap
    return { msg, key: msg.message_id != null ? `m-${msg.message_id}` : `i-${i}`, newDay, startOfGroup }
  })
}

interface Props {
  messages: FeedMessage[]
  total: number
  height?: string
  highlight?: string
}

export default function ChatBubbleFeed({ messages, total, height = '18rem', highlight = '' }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)

  // Show sender labels only in group chats (more than one non-me participant).
  const showNames = useMemo(() => {
    const others = new Set(messages.filter((m) => m.sender_id !== 'me').map((m) => m.sender_id))
    return others.size > 1
  }, [messages])

  const colorMap = useMemo(() => {
    const map = new Map<string, string>()
    for (const m of messages) if (!map.has(m.sender_id)) map.set(m.sender_id, senderColor(m.sender_id))
    return map
  }, [messages])

  const items = useMemo(() => buildItems(messages), [messages])

  // Open scrolled to the newest message (bottom), WhatsApp-style.
  useLayoutEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [items])

  function jumpTo(id: number) {
    const el = document.getElementById(`msg-${id}`)
    if (!el) return
    el.scrollIntoView({ block: 'center', behavior: 'smooth' })
    el.classList.add('ring-2', 'ring-accent')
    window.setTimeout(() => el.classList.remove('ring-2', 'ring-accent'), 1200)
  }

  return (
    <div className="space-y-2">
      <p className="text-[10px] text-tx-muted">
        {messages.length < total
          ? `${messages.length.toLocaleString()} of ${total.toLocaleString()} messages`
          : `${messages.length.toLocaleString()} messages`}
      </p>

      <div
        ref={scrollRef}
        className="overflow-y-auto rounded-lg bg-app-bg border border-app-border px-3 py-2"
        style={{ height }}
      >
        {items.length === 0 ? (
          <div className="flex items-center justify-center h-full text-tx-muted text-sm">No messages</div>
        ) : (
          items.map((item) => (
            <div key={item.key} className={item.startOfGroup ? 'mt-2 first:mt-0' : 'mt-0.5'}>
              {item.newDay && <DaySeparator day={dayKey(item.msg.timestamp)} />}
              <Bubble
                msg={item.msg}
                showName={showNames && item.startOfGroup}
                color={colorMap.get(item.msg.sender_id) ?? CHAT_COLORS[0]}
                highlight={highlight}
                onJump={jumpTo}
              />
            </div>
          ))
        )}
      </div>
    </div>
  )
}
