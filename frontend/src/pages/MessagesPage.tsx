import { useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import MessageFeed from '../components/MessageFeed'

const PAGE_SIZE = 2000

export default function MessagesPage() {
  const { chatId } = useParams<{ chatId: string }>()
  const [offset, setOffset] = useState(0)

  const { data, isLoading } = useQuery({
    queryKey: ['chat-messages', chatId, offset],
    queryFn: () => api.chatMessages(Number(chatId), PAGE_SIZE, offset),
    enabled: !!chatId,
  })

  const senders: string[] = useMemo(() => {
    if (!data) return []
    const freq = new Map<string, number>()
    for (const m of data.messages) freq.set(m.sender_name, (freq.get(m.sender_name) ?? 0) + 1)
    return [...freq.entries()].sort((a, b) => b[1] - a[1]).map(([s]) => s)
  }, [data])

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0
  const currentPage = Math.floor(offset / PAGE_SIZE)

  if (isLoading) {
    return <div className="h-64 bg-app-surface border border-app-border rounded-xl animate-pulse" />
  }

  if (!data || data.total === 0) {
    return (
      <div className="bg-app-surface border border-app-border rounded-xl p-8 text-center text-slate-500 text-sm">
        No messages
      </div>
    )
  }

  return (
    <div className="bg-app-surface border border-app-border rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
          Message History
        </h3>
        {totalPages > 1 && (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <button
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              disabled={offset === 0}
              className="px-2 py-1 rounded bg-app-surface-2 border border-app-border disabled:opacity-30 hover:text-slate-200 transition-colors"
            >
              ← Older
            </button>
            <span className="tabular-nums">
              page {currentPage + 1} / {totalPages}
            </span>
            <button
              onClick={() => setOffset(offset + PAGE_SIZE)}
              disabled={offset + PAGE_SIZE >= data.total}
              className="px-2 py-1 rounded bg-app-surface-2 border border-app-border disabled:opacity-30 hover:text-slate-200 transition-colors"
            >
              Newer →
            </button>
          </div>
        )}
      </div>

      <MessageFeed
        messages={data.messages}
        total={data.total}
        senders={senders}
        showChat={false}
        dayOnly={false}
        height="calc(100vh - 280px)"
      />
    </div>
  )
}
