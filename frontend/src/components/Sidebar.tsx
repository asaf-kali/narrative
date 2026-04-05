import { useState } from 'react'
import { NavLink, Link } from 'react-router-dom'
import type { Chat } from '../api/types'

interface Props {
  chats: Chat[]
  isLoading: boolean
}

const TYPE_ICONS: Record<string, string> = {
  group: '👥',
  direct: '👤',
  broadcast: '📢',
}

export default function Sidebar({ chats, isLoading }: Props) {
  const [search, setSearch] = useState('')

  const filtered = chats.filter((c) => c.display_name.toLowerCase().includes(search.toLowerCase()))

  return (
    <aside className="w-72 bg-slate-900 text-slate-100 flex flex-col flex-shrink-0 overflow-hidden">
      <div className="p-4 border-b border-slate-700">
        <Link to="/" className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 hover:text-teal-400 transition-colors">
          ← All Chats ({chats.length})
        </Link>
        <input
          type="text"
          placeholder="Search chats..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-slate-800 text-slate-100 placeholder-slate-400 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
        />
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {isLoading && <div className="text-slate-400 text-sm p-4 text-center">Loading...</div>}
        {filtered.map((chat) => (
          <NavLink
            key={chat.chat_id}
            to={`/chat/${chat.chat_id}`}
            className={({ isActive }) =>
              `flex flex-col px-3 py-2 rounded-lg mb-1 text-sm transition-colors ${
                isActive ? 'bg-teal-600 text-white' : 'text-slate-300 hover:bg-slate-800'
              }`
            }
          >
            <span className="font-medium truncate">
              {TYPE_ICONS[chat.chat_type] ?? '💬'} {chat.display_name}
            </span>
            <span className="text-xs opacity-60">{chat.message_count.toLocaleString()} messages</span>
          </NavLink>
        ))}
      </div>
    </aside>
  )
}
