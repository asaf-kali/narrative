import type { ReactNode } from 'react'
import type { FeedMessage } from '../../api/types'
import MessageFeed from '../MessageFeed'

// ── component ─────────────────────────────────────────────────────────────────

interface Props {
  messages: FeedMessage[]
  total: number
  showChat?: boolean
  dayOnly?: boolean
  height?: string
  highlight?: string
  /** Optional content rendered in a header bar above the feed (e.g. pagination). */
  header?: ReactNode
  onChatClick?: (chatId: string) => void
  onSenderClick?: (senderId: string) => void
}

export default function MessagesCard({
  messages,
  total,
  showChat,
  dayOnly,
  height,
  highlight,
  header,
  onChatClick,
  onSenderClick,
}: Props) {
  return (
    <div className="bg-app-surface border border-app-border rounded-xl overflow-hidden">
      {header && (
        <div className="px-4 py-2.5 border-b border-app-border flex items-center gap-3">
          {header}
        </div>
      )}
      <div className="p-4">
        <MessageFeed
          messages={messages}
          total={total}
          showChat={showChat}
          dayOnly={dayOnly}
          height={height}
          highlight={highlight}
          onChatClick={onChatClick}
          onSenderClick={onSenderClick}
        />
      </div>
    </div>
  )
}
