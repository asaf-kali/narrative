import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { api } from '../api/client'
import { CardSpinner } from '../components/Spinner'
import type { ReactionStat, ReplyStat, TopReactedMessage } from '../api/types'

const TOOLTIP_STYLE = { background: '#0d0f17', border: '1px solid #1a1d2e', color: '#e2e8f0', borderRadius: 8, fontSize: 12 }
const TICK_STYLE = { fill: '#64748b', fontSize: 10 }

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-app-surface border border-app-border rounded-xl p-4 overflow-x-auto">
      <h3 className="text-xs font-semibold text-tx-secondary uppercase tracking-widest mb-4">{title}</h3>
      {children}
    </div>
  )
}

function LeaderboardTable({ headers, rows }: { headers: string[]; rows: (string | number)[][] }) {
  if (rows.length === 0) return <div className="text-tx-muted text-sm py-6 text-center">No data</div>
  return (
    <table className="w-full text-xs">
      <thead>
        <tr className="text-left border-b border-app-border">
          {headers.map((h) => (
            <th key={h} className="py-2 pr-4 text-tx-muted font-medium">{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i} className="border-b border-app-border/50 hover:bg-app-hover transition-colors">
            {row.map((cell, j) => (
              <td
                key={j}
                className={`py-2.5 pr-4 ${j === 0 ? 'font-medium text-tx-primary' : 'tabular-nums text-tx-secondary'}`}
              >
                {typeof cell === 'number' ? cell.toLocaleString() : cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function reactionRows(data: ReactionStat[]): (string | number)[][] {
  return data.slice(0, 30).map((r) => [r.sender_name, r.reactions_received, r.reactions_given])
}

function replyRows(data: ReplyStat[]): (string | number)[][] {
  return data.slice(0, 30).map((r) => [r.sender_name, r.replies_received, r.replies_sent])
}

function TopReacted({ rows }: { rows: TopReactedMessage[] }) {
  if (rows.length === 0) return <div className="text-tx-muted text-sm py-6 text-center">No reactions</div>
  return (
    <div className="space-y-1.5">
      {rows.map((m) => (
        <div key={m.message_id} className="flex items-center gap-3 py-1.5 border-b border-app-border/50">
          <span className="text-[11px] font-medium text-tx-secondary w-28 flex-shrink-0 truncate">{m.sender_name}</span>
          <span className="text-xs text-tx-secondary min-w-0 truncate flex-1">{m.text ?? '[Media]'}</span>
          <span className="text-xs flex-shrink-0">{m.emojis}</span>
        </div>
      ))}
    </div>
  )
}

export default function EngagementPage() {
  const { chatId } = useParams<{ chatId: string }>()
  const { data, isLoading } = useQuery({
    queryKey: ['engagement', chatId],
    queryFn: () => api.engagement(Number(chatId)),
    enabled: !!chatId,
  })

  if (isLoading || !data) return (
    <div className="bg-app-surface border border-app-border rounded-xl">
      <CardSpinner className="h-64" />
    </div>
  )

  return (
    <div className="space-y-4">
      <Card title="Reaction Emojis">
        {data.emoji_breakdown.length === 0 ? (
          <div className="text-tx-muted text-sm py-6 text-center">No reactions in this chat</div>
        ) : (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data.emoji_breakdown.slice(0, 20)} layout="vertical">
              <XAxis type="number" tick={TICK_STYLE} />
              <YAxis type="category" dataKey="emoji" tick={{ fontSize: 16, fill: '#94a3b8' }} width={40} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Bar dataKey="count" name="Count" fill="#7c5af6" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>

      <div className="grid grid-cols-2 gap-4">
        <Card title="Reactions — Received vs Given">
          <LeaderboardTable headers={['Name', 'Received', 'Given']} rows={reactionRows(data.reaction_leaderboard)} />
        </Card>
        <Card title="Replies — Received vs Sent">
          <LeaderboardTable headers={['Name', 'Received', 'Sent']} rows={replyRows(data.reply_leaderboard)} />
        </Card>
      </div>

      <Card title="Most Reacted Messages">
        <TopReacted rows={data.top_reacted} />
      </Card>
    </div>
  )
}
