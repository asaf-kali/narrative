import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { DayCount } from '../api/types'
import CalendarHeatmap from '../components/CalendarHeatmap'

type Range = '1M' | '3M' | '6M' | '1Y' | 'ALL'

const RANGES: { label: string; value: Range }[] = [
  { label: '1 month', value: '1M' },
  { label: '3 months', value: '3M' },
  { label: '6 months', value: '6M' },
  { label: '1 year', value: '1Y' },
  { label: 'All time', value: 'ALL' },
]

function cutoffDate(range: Range): string | null {
  if (range === 'ALL') return null
  const months = { '1M': 1, '3M': 3, '6M': 6, '1Y': 12 }[range]
  const d = new Date()
  d.setMonth(d.getMonth() - months)
  return d.toISOString().slice(0, 10)
}

function filterData(data: DayCount[], range: Range): DayCount[] {
  const cutoff = cutoffDate(range)
  return cutoff ? data.filter((d) => d.date >= cutoff) : data
}

export default function HomePage() {
  const [range, setRange] = useState<Range>('1M')
  const [selectedDate, setSelectedDate] = useState<string | null>(null)

  const { data: allData = [], isLoading } = useQuery({
    queryKey: ['daily-counts'],
    queryFn: api.dailyCounts,
  })

  const data = useMemo(() => filterData(allData, range), [allData, range])

  const totalMessages = data.reduce((sum, d) => sum + d.count, 0)
  const activeDays = data.filter((d) => d.count > 0).length
  const peakDay = data.reduce((best, d) => (d.count > best.count ? d : best), { date: '—', count: 0 })

  const handleRangeChange = (r: Range) => {
    setRange(r)
    if (selectedDate) {
      const cutoff = cutoffDate(r)
      if (cutoff && selectedDate < cutoff) setSelectedDate(null)
    }
  }

  return (
    <div className="max-w-5xl space-y-5">
      <div>
        <h2 className="text-xl font-bold text-slate-100">All Chats</h2>
        <p className="text-xs text-slate-500 mt-1">Activity across all conversations</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Total Messages" value={totalMessages.toLocaleString()} icon="💬" />
        <StatCard label="Active Days" value={activeDays.toLocaleString()} icon="📅" />
        <StatCard label="Busiest Day" value={peakDay.date} sub={`${peakDay.count.toLocaleString()} messages`} icon="🔥" />
      </div>

      <div className="bg-app-surface border border-app-border rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest">Message Activity</h3>
          <div className="flex gap-1.5">
            {RANGES.map((r) => (
              <button
                key={r.value}
                onClick={() => handleRangeChange(r.value)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  range === r.value
                    ? 'bg-accent text-white shadow-lg shadow-accent/20'
                    : 'bg-app-surface-2 text-slate-400 hover:text-slate-200 border border-app-border'
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>
        {isLoading ? (
          <div className="h-36 bg-app-surface-2 rounded animate-pulse" />
        ) : (
          <CalendarHeatmap data={data} selectedDate={selectedDate} onSelectDate={setSelectedDate} />
        )}
      </div>

      {selectedDate && (
        <div className="bg-app-surface border border-accent/30 rounded-xl p-5">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-slate-300">
              {selectedDate} —{' '}
              <span className="text-accent-light">
                {allData.find((d) => d.date === selectedDate)?.count.toLocaleString()} messages
              </span>
            </h3>
            <button onClick={() => setSelectedDate(null)} className="text-slate-500 hover:text-slate-300 text-sm transition-colors">
              ✕
            </button>
          </div>
          <p className="text-slate-500 text-xs italic">
            Per-day chat breakdown coming soon — will show active chats, top senders, and hourly distribution.
          </p>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, sub, icon }: { label: string; value: string; sub?: string; icon: string }) {
  return (
    <div className="bg-app-surface border border-app-border rounded-xl p-4">
      <div className="text-[11px] text-slate-400 mb-1.5">
        {icon} {label}
      </div>
      <div className="text-2xl font-bold text-slate-100 tabular-nums">{value}</div>
      {sub && <div className="text-[11px] text-slate-500 mt-0.5">{sub}</div>}
    </div>
  )
}
