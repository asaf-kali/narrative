import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { api } from '../api/client'

const DONUT_COLORS = ['#0d9488', '#0891b2', '#7c3aed', '#db2777', '#f59e0b', '#84cc16', '#6366f1', '#94a3b8']

function StatCard({ icon, label, value }: { icon: string; label: string; value: string | number }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <div className="text-gray-400 text-sm mb-1">
        {icon} {label}
      </div>
      <div className="text-2xl font-bold text-gray-800">
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
        <div className="col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm p-4">
          <h3 className="text-sm font-semibold text-gray-600 mb-3">Activity (last 30 days)</h3>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={data.sparkline}>
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v: string) => v.slice(5)} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#0d9488"
                fill="#99f6e4"
                strokeWidth={2}
                name="Messages"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
          <h3 className="text-sm font-semibold text-gray-600 mb-3">Message Types</h3>
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
              <Tooltip formatter={(v: number) => v.toLocaleString()} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="grid grid-cols-6 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-gray-200 rounded-xl h-20" />
        ))}
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 bg-gray-200 rounded-xl h-56" />
        <div className="bg-gray-200 rounded-xl h-56" />
      </div>
    </div>
  )
}
