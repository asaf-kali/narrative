import { useState } from 'react'
import { NavLink, Link } from 'react-router-dom'
import type { Chat } from '../api/types'

interface Props { chats: Chat[]; isLoading: boolean }

const TYPE_ICONS: Record<string, string> = { group: '⬡', direct: '◎', broadcast: '◈' }

export default function Sidebar({ chats, isLoading }: Props) {
  const [search, setSearch] = useState('')
  const [hideEmpty, setHideEmpty] = useState(true)
  const filtered = chats.filter((c) => {
    if (hideEmpty && c.message_count === 0) return false
    return c.display_name.toLowerCase().includes(search.toLowerCase())
  })

  return (
    <aside className="w-64 bg-[#06070c] border-r border-app-border flex flex-col flex-shrink-0 h-full">
      {/* Brand */}
      <div className="px-5 py-5 border-b border-app-border">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center text-white text-xs font-bold shadow-lg shadow-accent/30">
            W
          </div>
          <span className="font-semibold text-sm text-slate-100 tracking-tight">WA Analyzer</span>
        </Link>
        <div className="mt-3.5 relative">
          <svg className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-app-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
          </svg>
          <input
            type="text"
            placeholder="Search chats…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-app-surface border border-app-border rounded-lg pl-8 pr-3 py-2 text-xs text-slate-300 placeholder-app-muted focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all"
          />
        </div>
      </div>

      {/* Global nav */}
      <div className="px-2 pt-2 pb-1 border-b border-app-border">
        <NavLink
          to="/network"
          className={({ isActive }) =>
            `flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-medium transition-all ${
              isActive
                ? 'bg-accent/10 text-slate-100'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
            }`
          }
        >
          <span className="text-[10px] opacity-60">◎</span>
          <span>Global Network</span>
        </NavLink>
      </div>

      {/* Chat count label + hide-empty toggle */}
      <div className="px-5 pt-3 pb-1 flex items-center justify-between">
        <span className="text-[10px] font-semibold text-app-muted uppercase tracking-widest">
          {filtered.length} chats
        </span>
        <label className="flex items-center gap-1.5 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={hideEmpty}
            onChange={(e) => setHideEmpty(e.target.checked)}
            className="w-3 h-3 accent-accent"
          />
          <span className="text-[10px] text-app-muted">Hide empty</span>
        </label>
      </div>

      {/* Chat list */}
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {isLoading && (
          <div className="space-y-1.5 px-3 pt-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-9 rounded-md bg-app-surface animate-pulse" style={{ opacity: 1 - i * 0.12 }} />
            ))}
          </div>
        )}
        {filtered.map((chat) => (
          <NavLink
            key={chat.chat_id}
            to={`/chat/${chat.chat_id}`}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2 rounded-md mb-0.5 text-xs transition-all group relative ${
                isActive
                  ? 'bg-accent/10 text-slate-100 border-l-2 border-accent pl-[10px]'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] border-l-2 border-transparent pl-[10px]'
              }`
            }
          >
            <span className="text-[10px] opacity-50 w-3 flex-shrink-0">{TYPE_ICONS[chat.chat_type] ?? '○'}</span>
            <span className="truncate font-medium">{chat.display_name}</span>
            <span className="ml-auto text-[10px] opacity-40 flex-shrink-0 tabular-nums">
              {chat.message_count >= 1000 ? `${(chat.message_count / 1000).toFixed(1)}k` : chat.message_count}
            </span>
          </NavLink>
        ))}
      </div>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-app-border">
        <p className="text-[10px] text-app-muted">All processing is local</p>
      </div>
    </aside>
  )
}
