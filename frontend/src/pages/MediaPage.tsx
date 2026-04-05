import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { PieChart, Pie, Cell, Tooltip, Legend, BarChart, Bar, XAxis, YAxis, ResponsiveContainer } from 'recharts'
import { api } from '../api/client'

const COLORS = ['#7c5af6', '#0891b2', '#0d9488', '#db2777', '#f59e0b', '#84cc16', '#6366f1', '#94a3b8']
const TOOLTIP_STYLE = { background: '#0d0f17', border: '1px solid #1a1d2e', color: '#e2e8f0', borderRadius: 8, fontSize: 12 }
const TICK_STYLE = { fill: '#64748b', fontSize: 10 }

export default function MediaPage() {
  const { chatId } = useParams<{ chatId: string }>()
  const { data, isLoading } = useQuery({
    queryKey: ['media', chatId],
    queryFn: () => api.media(Number(chatId)),
    enabled: !!chatId,
  })

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-app-surface border border-app-border rounded-xl h-80 animate-pulse" />
        <div className="bg-app-surface border border-app-border rounded-xl h-80 animate-pulse" />
      </div>
    )
  }

  // Pivot timeline for stacked bar
  const typeLabels = [...new Set((data?.timeline ?? []).map((r) => r.type_label))]
  const monthMap = new Map<string, Record<string, unknown>>()
  for (const row of data?.timeline ?? []) {
    if (!monthMap.has(row.month)) monthMap.set(row.month, { month: row.month })
    monthMap.get(row.month)![row.type_label] = row.count
  }
  const timelineRows = [...monthMap.values()]

  return (
    <div className="grid grid-cols-5 gap-4">
      <div className="col-span-2 bg-app-surface border border-app-border rounded-xl p-4">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-4">Media Breakdown</h3>
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={data?.breakdown ?? []}
              dataKey="count"
              nameKey="type_label"
              cx="50%"
              cy="45%"
              innerRadius={50}
              outerRadius={90}
            >
              {(data?.breakdown ?? []).map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => v.toLocaleString()} />
            <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="col-span-3 bg-app-surface border border-app-border rounded-xl p-4">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-4">Media Over Time</h3>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={timelineRows}>
            <XAxis dataKey="month" tick={TICK_STYLE} />
            <YAxis tick={TICK_STYLE} />
            <Tooltip contentStyle={TOOLTIP_STYLE} />
            <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
            {typeLabels.map((label, i) => (
              <Bar key={label} dataKey={label} stackId="a" fill={COLORS[i % COLORS.length]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
