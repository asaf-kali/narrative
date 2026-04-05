import { useMemo, useRef, useState } from 'react'
import type { FeedMessage } from '../api/types'

// ── palette ──────────────────────────────────────────────────────────────────

export const CHAT_COLORS = [
  '#7c5af6', '#0891b2', '#0d9488', '#db2777',
  '#f59e0b', '#84cc16', '#6366f1', '#e879f9',
]
const FALLBACK_COLOR = '#374061'
const MAX_LABELED_CHATS = 8

export function buildChatColorMap(chats: string[]): Map<string, string> {
  const map = new Map<string, string>()
  chats.forEach((c, i) => map.set(c, i < MAX_LABELED_CHATS ? CHAT_COLORS[i % CHAT_COLORS.length] : FALLBACK_COLOR))
  return map
}

// ── helpers ───────────────────────────────────────────────────────────────────

function shortName(name: string, max = 20): string {
  return name.length > max ? name.slice(0, max - 1) + '…' : name
}

/** Format ISO timestamp for display. In day-only mode strip the date prefix. */
function formatTime(ts: string, dayOnly: boolean): string {
  // ts is "YYYY-MM-DDTHH:MM:SS"
  if (dayOnly) return ts.slice(11, 16)          // "HH:MM"
  return ts.slice(0, 10) + ' ' + ts.slice(11, 16) // "YYYY-MM-DD HH:MM"
}

// ── sub-components ────────────────────────────────────────────────────────────

interface RowProps {
  msg: FeedMessage
  chatColor: string
  dayOnly: boolean
  showChat: boolean
}

function MessageRow({ msg, chatColor, dayOnly, showChat }: RowProps) {
  return (
    <div className="flex items-baseline gap-3 px-3 py-1.5 hover:bg-white/[0.025] rounded transition-colors min-w-0">
      <span className="text-[11px] text-slate-500 tabular-nums flex-shrink-0 w-28">
        {formatTime(msg.timestamp, dayOnly)}
      </span>
      {showChat && (
        <span
          className="text-[10px] font-medium px-1.5 py-0.5 rounded flex-shrink-0 max-w-[140px] truncate"
          style={{ backgroundColor: chatColor + '22', color: chatColor }}
          title={msg.chat_name}
        >
          {shortName(msg.chat_name, 18)}
        </span>
      )}
      <span className="text-xs font-medium text-slate-300 flex-shrink-0 w-28 truncate" title={msg.sender_name}>
        {msg.sender_name}
      </span>
      <span className={`text-xs min-w-0 truncate ${msg.text?.startsWith('[') ? 'text-slate-500 italic' : 'text-slate-400'}`}>
        {msg.text ?? ''}
      </span>
    </div>
  )
}

// ── main component ────────────────────────────────────────────────────────────

interface Props {
  messages: FeedMessage[]
  total: number             // total available (may be > messages.length if paginated)
  senders: string[]         // ordered by frequency desc, for filter chips
  showChat?: boolean        // show chat-name badge column (default: true)
  dayOnly?: boolean         // timestamps are all same day → show only HH:MM (default: false)
  height?: string           // css height of scroll container (default: "18rem")
}

export default function MessageFeed({
  messages,
  total,
  senders,
  showChat = true,
  dayOnly = false,
  height = '18rem',
}: Props) {
  const [activeSenders, setActiveSenders] = useState<Set<string>>(new Set())
  const feedRef = useRef<HTMLDivElement>(null)

  const chatColorMap = useMemo(() => {
    const chats = [...new Set(messages.map((m) => m.chat_name))]
    return buildChatColorMap(chats)
  }, [messages])

  const filtered = useMemo(
    () => (activeSenders.size === 0 ? messages : messages.filter((m) => activeSenders.has(m.sender_name))),
    [messages, activeSenders]
  )

  function toggleSender(sender: string) {
    setActiveSenders((prev) => {
      const next = new Set(prev)
      if (next.has(sender)) next.delete(sender)
      else next.add(sender)
      return next
    })
  }

  return (
    <div className="space-y-2">
      {/* Sender filter chips */}
      {senders.length > 1 && (
        <div className="flex flex-wrap gap-1.5">
          {senders.slice(0, 20).map((s) => (
            <button
              key={s}
              onClick={() => toggleSender(s)}
              className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors border ${
                activeSenders.has(s)
                  ? 'bg-accent/15 border-accent/50 text-accent-light'
                  : 'bg-app-surface-2 border-app-border text-slate-400 hover:text-slate-200'
              }`}
            >
              {s}
            </button>
          ))}
          {activeSenders.size > 0 && (
            <button
              onClick={() => setActiveSenders(new Set())}
              className="px-2.5 py-1 rounded-full text-[11px] text-slate-500 hover:text-slate-300 transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      )}

      {/* Count label */}
      <p className="text-[10px] text-slate-500">
        {filtered.length < total
          ? `${filtered.length.toLocaleString()} of ${total.toLocaleString()} messages`
          : `${filtered.length.toLocaleString()} messages`}
        {total > messages.length && (
          <span className="ml-1 text-slate-600">(showing last {messages.length.toLocaleString()})</span>
        )}
      </p>

      {/* Scroll container */}
      <div
        ref={feedRef}
        className="overflow-y-auto rounded-lg bg-app-bg border border-app-border py-1"
        style={{ height }}
      >
        {filtered.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-500 text-sm">No messages</div>
        ) : (
          filtered.map((msg, i) => (
            <MessageRow
              key={i}
              msg={msg}
              chatColor={chatColorMap.get(msg.chat_name) ?? FALLBACK_COLOR}
              dayOnly={dayOnly}
              showChat={showChat}
            />
          ))
        )}
      </div>
    </div>
  )
}
