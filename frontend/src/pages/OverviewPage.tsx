import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { api } from '../api/client'
import { CardSpinner } from '../components/Spinner'

const DONUT_COLORS = ['#7c5af6', '#0891b2', '#db2777', '#f59e0b', '#84cc16', '#6366f1', '#0d9488', '#94a3b8']
const TOOLTIP_STYLE = { background: '#0d0f17', border: '1px solid #1a1d2e', color: '#e2e8f0', borderRadius: 8, fontSize: 12 }
const TICK_STYLE = { fill: '#64748b', fontSize: 11 }

function StatCard({ icon, label, value }: { icon: string; label: string; value: string | number }) {
  return (
    <div className="bg-app-surface border border-app-border rounded-xl p-4">
      <div className="text-[11px] text-slate-400 mb-1.5">
        {icon} {label}
      </div>
      <div className="text-2xl font-bold text-slate-100 tabular-nums">
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
    </div>
  )
}

export default function OverviewPage() {
  const { chatId } = useParams<{ chatId: string }>()
  const { data, isLoading } = useQuery({
    queryKey: ['overview', chatId],
    queryFn: () => api.overview(Number(chatId)),
    enabled: !!chatId,
  })

  if (isLoading) return <LoadingState />
  if (!data) return null

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-6 gap-3">
        <StatCard icon="💬" label="Messages" value={data.total_messages} />
        <StatCard icon="📅" label="Active Days" value={data.active_days} />
        <StatCard icon="🖼️" label="Media" value={data.total_media} />
        <StatCard icon="🎙️" label="Voice Notes" value={data.total_audio} />
        <StatCard icon="🔗" label="Links" value={data.total_links} />
        <StatCard icon="📊" label="Types" value={data.type_breakdown.length} />
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 bg-app-surface border border-app-border rounded-xl p-4">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-4">Activity</h3>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={data.sparkline}>
              <XAxis dataKey="date" tick={TICK_STYLE} tickFormatter={(v: string) => v.slice(0, 7)} interval="preserveStartEnd" />
              <YAxis tick={TICK_STYLE} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#7c5af6"
                fill="#7c5af6"
                fillOpacity={0.15}
                strokeWidth={2}
                name="Messages"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-app-surface border border-app-border rounded-xl p-4">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-4">Message Types</h3>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie
                data={data.type_breakdown}
                dataKey="count"
                nameKey="label"
                cx="50%"
                cy="50%"
                innerRadius={40}
                outerRadius={70}
              >
                {data.type_breakdown.map((_, i) => (
                  <Cell key={i} fill={DONUT_COLORS[i % DONUT_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => v.toLocaleString()} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-6 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-app-surface border border-app-border rounded-xl p-4">
            <CardSpinner className="h-12" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 bg-app-surface border border-app-border rounded-xl p-4">
          <CardSpinner className="h-48" />
        </div>
        <div className="bg-app-surface border border-app-border rounded-xl p-4">
          <CardSpinner className="h-48" />
        </div>
      </div>
    </div>
  )
}
