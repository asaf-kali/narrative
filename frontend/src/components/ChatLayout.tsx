import { NavLink, Outlet, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { Chat } from '../api/types'

const TABS = [
  { label: 'Overview', path: '' },
  { label: 'Timeline', path: 'timeline' },
  { label: 'Participants', path: 'participants' },
  { label: 'Words & Emoji', path: 'content' },
  { label: 'Media', path: 'media' },
  { label: 'Messages', path: 'messages' },
]

const TYPE_LABEL: Record<string, string> = { direct: 'Direct', group: 'Group', broadcast: 'Broadcast' }
const TYPE_COLOR: Record<string, string> = {
  direct: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
  group: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
  broadcast: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function Chip({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[9px] font-semibold uppercase tracking-widest text-slate-500">{label}</span>
      <span className={`text-xs text-slate-300 ${mono ? 'font-mono' : ''}`}>{value}</span>
    </div>
  )
}

function ChatHeader({ chat }: { chat: Chat }) {
  const phoneLabel = chat.is_lid ? 'LID' : 'Phone'
  const dateRange = `${formatDate(chat.date_first)} → ${formatDate(chat.date_last)}`

  return (
    <div className="px-5 pt-4 pb-0 border-b border-app-border bg-app-surface/40">
      <div className="flex items-start justify-between gap-4 mb-3">
        {/* Name + type badge */}
        <div className="flex items-center gap-2.5 min-w-0">
          <h1 className="text-base font-bold text-slate-100 truncate">{chat.display_name}</h1>
          <span className={`shrink-0 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${TYPE_COLOR[chat.chat_type]}`}>
            {TYPE_LABEL[chat.chat_type]}
          </span>
        </div>

        {/* Meta chips */}
        <div className="flex items-start gap-5 shrink-0 text-right">
          <Chip label="Chat ID" value={String(chat.chat_id)} mono />
          {chat.phone && <Chip label={phoneLabel} value={chat.phone} mono />}
          <Chip label="Messages" value={chat.message_count.toLocaleString()} />
          <Chip label="Active" value={dateRange} />
        </div>
      </div>

      {/* Tabs */}
      <nav className="flex gap-0.5">
        {TABS.map((tab) => (
          <NavLink
            key={tab.path}
            to={tab.path === '' ? `/chat/${chat.chat_id}` : `/chat/${chat.chat_id}/${tab.path}`}
            end={tab.path === ''}
            className={({ isActive }) =>
              `px-3.5 py-2 text-xs font-medium rounded-t-md border-b-2 -mb-px transition-colors ${
                isActive
                  ? 'border-accent text-slate-100 bg-app-surface-2'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
              }`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}

export default function ChatLayout() {
  const { chatId } = useParams<{ chatId: string }>()
  const { data: chats = [] } = useQuery({ queryKey: ['chats'], queryFn: api.chats })
  const chat = chats.find((c) => c.chat_id === Number(chatId))

  return (
    <div className="flex flex-col h-full">
      {chat ? (
        <ChatHeader chat={chat} />
      ) : (
        <div className="px-5 pt-4 pb-0 border-b border-app-border">
          <div className="h-14 bg-app-surface-2 rounded animate-pulse mb-3" />
          <nav className="flex gap-0.5">
            {TABS.map((tab) => (
              <div key={tab.path} className="h-8 w-20 bg-app-surface-2 rounded-t animate-pulse" />
            ))}
          </nav>
        </div>
      )}
      <div className="flex-1 overflow-auto p-5">
        <Outlet />
      </div>
    </div>
  )
}
