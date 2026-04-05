import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AreaChart, Area, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { api } from '../api/client'
import Heatmap from '../components/Heatmap'
import type { TimelinePoint } from '../api/types'

const COLORS = ['#7c5af6', '#0891b2', '#0d9488', '#db2777', '#f59e0b', '#84cc16', '#6366f1', '#94a3b8']
const TOOLTIP_STYLE = { background: '#0d0f17', border: '1px solid #1a1d2e', color: '#e2e8f0', borderRadius: 8, fontSize: 12 }
const TICK_STYLE = { fill: '#64748b', fontSize: 11 }

function pivotTimeline(data: TimelinePoint[]) {
  const senders = [...new Set(data.map((d) => d.sender_name))]
  const map = new Map<string, Record<string, number>>()
  for (const row of data) {
    if (!map.has(row.x)) map.set(row.x, { x: row.x as unknown as number })
    map.get(row.x)![row.sender_name] = row.count
  }
  return { rows: [...map.values()], senders }
}

export default function TimelinePage() {
  const { chatId } = useParams<{ chatId: string }>()
  const [period, setPeriod] = useState<'daily' | 'monthly'>('daily')

  const { data: timelineData = [], isLoading: tLoading } = useQuery({
    queryKey: ['timeline', chatId, period],
    queryFn: () => api.timeline(Number(chatId), period),
    enabled: !!chatId,
  })
  const { data: heatmapData = [], isLoading: hLoading } = useQuery({
    queryKey: ['heatmap', chatId],
    queryFn: () => api.heatmap(Number(chatId)),
    enabled: !!chatId,
  })

  const { rows, senders } = pivotTimeline(timelineData)

  return (
    <div className="space-y-4">
      <div className="bg-app-surface border border-app-border rounded-xl p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest">Message Timeline</h3>
          <div className="flex gap-1.5">
            {(['daily', 'monthly'] as const).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  period === p
                    ? 'bg-accent text-white shadow-lg shadow-accent/20'
                    : 'bg-app-surface-2 text-slate-400 hover:text-slate-200 border border-app-border'
                }`}
              >
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </button>
            ))}
          </div>
        </div>
        {tLoading ? (
          <div className="h-64 bg-app-surface-2 rounded animate-pulse" />
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={rows}>
              <XAxis dataKey="x" tick={TICK_STYLE} />
              <YAxis tick={TICK_STYLE} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
              {senders.slice(0, 8).map((sender, i) => (
                <Area
                  key={sender}
                  type="monotone"
                  dataKey={sender}
                  stackId="1"
                  stroke={COLORS[i % COLORS.length]}
                  fill={COLORS[i % COLORS.length]}
                  fillOpacity={0.5}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="bg-app-surface border border-app-border rounded-xl p-4">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-4">Activity Heatmap (Day × Hour)</h3>
        {hLoading ? <div className="h-40 bg-app-surface-2 rounded animate-pulse" /> : <Heatmap data={heatmapData} />}
      </div>
    </div>
  )
}
