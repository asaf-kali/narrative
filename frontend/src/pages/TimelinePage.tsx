import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AreaChart, Area, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { api } from '../api/client'
import Heatmap from '../components/Heatmap'
import type { TimelinePoint } from '../api/types'

const COLORS = ['#0d9488', '#0891b2', '#7c3aed', '#db2777', '#f59e0b', '#84cc16', '#6366f1', '#94a3b8']

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
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-600">Message Timeline</h3>
          <div className="flex gap-2">
            {(['daily', 'monthly'] as const).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  period === p ? 'bg-teal-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </button>
            ))}
          </div>
        </div>
        {tLoading ? (
          <div className="h-64 bg-gray-100 rounded animate-pulse" />
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={rows}>
              <XAxis dataKey="x" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              {senders.slice(0, 8).map((sender, i) => (
                <Area
                  key={sender}
                  type="monotone"
                  dataKey={sender}
                  stackId="1"
                  stroke={COLORS[i % COLORS.length]}
                  fill={COLORS[i % COLORS.length]}
                  fillOpacity={0.6}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
        <h3 className="text-sm font-semibold text-gray-600 mb-4">Activity Heatmap (Day x Hour)</h3>
        {hLoading ? <div className="h-40 bg-gray-100 rounded animate-pulse" /> : <Heatmap data={heatmapData} />}
      </div>
    </div>
  )
}
