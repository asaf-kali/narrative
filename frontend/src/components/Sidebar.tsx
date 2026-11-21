import { useState } from 'react'
import { NavLink, Link } from 'react-router-dom'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import logo from '../assets/logo.png'
import { api } from '../api/client'
import type { Chat, ChatSort } from '../api/types'
import { useDebounce } from '../hooks/useDebounce'

const TYPE_ICONS: Record<string, string> = { group: '⬡', direct: '◎', broadcast: '◈' }

const LIST_LIMIT = 100
const SORT_STORAGE_KEY = 'sidebar-chat-sort'

const SORTS: { value: ChatSort; label: string }[] = [
  { value: 'last', label: 'Last message' },
  { value: 'messages', label: 'Total messages' },
  { value: 'mine', label: 'My messages' },
]

function loadSort(): ChatSort {
  try {
    const stored = localStorage.getItem(SORT_STORAGE_KEY)
    return SORTS.some((s) => s.value === stored) ? (stored as ChatSort) : 'last'
  } catch {
    return 'last'
  }
}

function saveSort(sort: ChatSort) {
  try {
    localStorage.setItem(SORT_STORAGE_KEY, sort)
  } catch {
    // storage unavailable (private window etc.) — the choice just won't persist
  }
}

function formatCount(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)
}

export default function Sidebar() {
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<ChatSort>(loadSort)
  const debouncedSearch = useDebounce(search, 300)

  // One extra row tells us whether there are more than LIST_LIMIT chats.
  const { data = [], isLoading, isFetching } = useQuery({
    queryKey: ['chats', debouncedSearch, sort],
    queryFn: () => api.chats({ search: debouncedSearch || undefined, sort, hideEmpty: true, limit: LIST_LIMIT + 1 }),
    staleTime: 30_000,
    placeholderData: keepPreviousData,
  })
  const hasMore = data.length > LIST_LIMIT
  const chats = data.slice(0, LIST_LIMIT)
  const countOf = (chat: Chat) => (sort === 'mine' ? chat.my_message_count : chat.message_count)

  function changeSort(next: ChatSort) {
    setSort(next)
    saveSort(next)
  }

  return (
    <aside className="w-64 bg-app-sidebar border-r border-app-border flex flex-col flex-shrink-0 h-full">
      {/* Brand */}
      <div className="px-5 py-5 border-b border-app-border">
        <Link to="/" className="flex items-center gap-2.5 group">
          <img src={logo} alt="Narrative" className="h-7" />
          <span className="font-semibold text-sm text-tx-primary tracking-tight">Narrative</span>
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
            className="w-full bg-app-surface border border-app-border rounded-lg pl-8 pr-3 py-2 text-xs text-tx-secondary placeholder-app-muted focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all"
          />
        </div>
      </div>

      {/* Sort order */}
      <label className="px-5 pt-3 flex items-center gap-2">
        <span className="text-[10px] text-app-muted flex-shrink-0">Sort by</span>
        <select
          value={sort}
          onChange={(e) => changeSort(e.target.value as ChatSort)}
          className="flex-1 min-w-0 bg-app-surface border border-app-border rounded-md px-2 py-1 text-[11px] text-tx-secondary focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 cursor-pointer"
        >
          {SORTS.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>
      </label>

      {/* Chat count label (empty chats are always hidden) */}
      <div className="px-5 pt-2 pb-1">
        <span className={`text-[10px] font-semibold text-app-muted uppercase tracking-widest transition-opacity ${isFetching ? 'opacity-50' : ''}`}>
          {hasMore ? `${LIST_LIMIT}+` : chats.length} chats
        </span>
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
        {chats.map((chat) => (
          <NavLink
            key={chat.chat_id}
            to={`/chat/${chat.chat_id}`}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2 rounded-md mb-0.5 text-xs transition-all group relative ${
                isActive
                  ? 'bg-accent/10 text-tx-primary border-l-2 border-accent pl-[10px]'
                  : 'text-tx-secondary hover:text-tx-primary hover:bg-app-hover border-l-2 border-transparent pl-[10px]'
              }`
            }
          >
            <span className="text-[10px] opacity-50 w-3 flex-shrink-0">{TYPE_ICONS[chat.chat_type] ?? '○'}</span>
            <span className="truncate font-medium">{chat.display_name}</span>
            <span
              className="ml-auto text-[10px] opacity-40 flex-shrink-0 tabular-nums"
              title={sort === 'mine' ? 'Messages sent by me' : 'Messages'}
            >
              {formatCount(countOf(chat))}
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
