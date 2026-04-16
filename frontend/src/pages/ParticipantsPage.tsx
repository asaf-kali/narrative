import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { api } from '../api/client'
import { CardSpinner } from '../components/Spinner'

const COLORS = ['#7c5af6', '#0891b2', '#0d9488', '#db2777', '#f59e0b', '#84cc16', '#6366f1', '#94a3b8']
const TOOLTIP_STYLE = { background: '#0d0f17', border: '1px solid #1a1d2e', color: '#e2e8f0', borderRadius: 8, fontSize: 12 }
const TICK_STYLE = { fill: '#64748b', fontSize: 11 }

export default function ParticipantsPage() {
  const { chatId } = useParams<{ chatId: string }>()
  const { data = [], isLoading } = useQuery({
    queryKey: ['participants', chatId],
    queryFn: () => api.participants(Number(chatId)),
    enabled: !!chatId,
  })

  if (isLoading) return (
    <div className="bg-app-surface border border-app-border rounded-xl">
      <CardSpinner className="h-64" />
    </div>
  )

  return (
    <div className="space-y-4">
      <div className="bg-app-surface border border-app-border rounded-xl p-4">
        <h3 className="text-xs font-semibold text-tx-secondary uppercase tracking-widest mb-4">Message Distribution</h3>
        <ResponsiveContainer width="100%" height={Math.max(200, data.length * 36)}>
          <BarChart data={data} layout="vertical">
            <XAxis type="number" tick={TICK_STYLE} />
            <YAxis type="category" dataKey="sender_name" tick={TICK_STYLE} width={120} />
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => v.toLocaleString()} />
            <Bar dataKey="messages" name="Messages">
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-app-surface border border-app-border rounded-xl p-4 overflow-x-auto">
        <h3 className="text-xs font-semibold text-tx-secondary uppercase tracking-widest mb-4">Detailed Stats</h3>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left border-b border-app-border">
              {['Name', 'Messages', '%', 'Words', 'Avg words', 'Media', 'Audio'].map((h) => (
                <th key={h} className="py-2 pr-4 text-tx-muted font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((p, i) => (
              <tr key={i} className="border-b border-app-border/50 hover:bg-app-hover transition-colors">
                <td className="py-2.5 pr-4 font-medium text-tx-primary">{p.sender_name}</td>
                <td className="py-2.5 pr-4 tabular-nums text-tx-secondary">{p.messages.toLocaleString()}</td>
                <td className="py-2.5 pr-4 tabular-nums text-tx-secondary">{p.pct}%</td>
                <td className="py-2.5 pr-4 tabular-nums text-tx-secondary">{Number(p.words).toLocaleString()}</td>
                <td className="py-2.5 pr-4 tabular-nums text-tx-secondary">{p.avg_words}</td>
                <td className="py-2.5 pr-4 tabular-nums text-tx-secondary">{p.media}</td>
                <td className="py-2.5 pr-4 tabular-nums text-tx-secondary">{p.audio}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
