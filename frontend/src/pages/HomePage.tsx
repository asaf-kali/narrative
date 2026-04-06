import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { DayCount } from '../api/types'
import CalendarHeatmap from '../components/CalendarHeatmap'
import DayDetail from '../components/DayDetail'
import DatetimeInput, { DATETIME_RE, formatDatetime } from '../components/DatetimeInput'

type Range = '1M' | '3M' | '6M' | '1Y' | 'ALL'

const RANGES: { label: string; value: Range }[] = [
  { label: '1M', value: '1M' },
  { label: '3M', value: '3M' },
  { label: '6M', value: '6M' },
  { label: '1Y', value: '1Y' },
  { label: 'All', value: 'ALL' },
]

function cutoffDate(range: Range): Date | null {
  if (range === 'ALL') return null
  const months = { '1M': 1, '3M': 3, '6M': 6, '1Y': 12 }[range]
  const d = new Date()
  d.setMonth(d.getMonth() - months)
  d.setHours(0, 0, 0, 0)
  return d
}

function filterData(data: DayCount[], from: string, to: string): DayCount[] {
  const fromDate = DATETIME_RE.test(from) ? from.slice(0, 10) : null
  const toDate = DATETIME_RE.test(to) ? to.slice(0, 10) : null
  return data.filter((d) => {
    if (fromDate && d.date < fromDate) return false
    if (toDate && d.date > toDate) return false
    return true
  })
}

export default function HomePage() {
  const [range, setRange] = useState<Range | null>('1M')
  const [customFrom, setCustomFrom] = useState('')
  const [customTo, setCustomTo] = useState('')
  const [selectedDate, setSelectedDate] = useState<string | null>(null)

  const { data: allData = [], isLoading } = useQuery({
    queryKey: ['daily-counts'],
    queryFn: api.dailyCounts,
  })

  // When a preset is active, derive from/to from it; otherwise use custom inputs
  const effectiveFrom = useMemo(() => {
    if (range === null) return customFrom
    const cutoff = cutoffDate(range)
    return cutoff ? formatDatetime(cutoff) : ''
  }, [range, customFrom])

  const effectiveTo = range === null ? customTo : ''

  const data = useMemo(
    () => filterData(allData, effectiveFrom, effectiveTo),
    [allData, effectiveFrom, effectiveTo],
  )

  const totalMessages = data.reduce((sum, d) => sum + d.count, 0)
  const activeDays = data.filter((d) => d.count > 0).length
  const peakDay = data.reduce((best, d) => (d.count > best.count ? d : best), { date: '—', count: 0 })

  function handleRangeClick(r: Range) {
    setRange(r)
    setCustomFrom('')
    setCustomTo('')
    if (selectedDate) {
      const cutoff = cutoffDate(r)
      if (cutoff && selectedDate < cutoff.toISOString().slice(0, 10)) setSelectedDate(null)
    }
  }

  function handleCustomChange(from: string, to: string) {
    setRange(null)
    setCustomFrom(from)
    setCustomTo(to)
  }

  const rangeInvalid = !!(
    DATETIME_RE.test(customFrom) &&
    DATETIME_RE.test(customTo) &&
    customTo < customFrom
  )

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
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest flex-shrink-0">Message Activity</h3>

          {/* Preset chips */}
          <div className="flex gap-1.5">
            {RANGES.map((r) => (
              <button
                key={r.value}
                onClick={() => handleRangeClick(r.value)}
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

          {/* Custom date range */}
          <div className="flex items-center gap-2 text-xs ml-auto">
            <DatetimeInput
              value={customFrom}
              onChange={(v) => handleCustomChange(v, customTo)}
              isInvalid={(!!customFrom && !DATETIME_RE.test(customFrom)) || rangeInvalid}
            />
            <span className={rangeInvalid ? 'text-red-400' : 'text-slate-500'}>→</span>
            <DatetimeInput
              value={customTo}
              onChange={(v) => handleCustomChange(customFrom, v)}
              isInvalid={(!!customTo && !DATETIME_RE.test(customTo)) || rangeInvalid}
            />
            {rangeInvalid && (
              <span className="text-red-400 text-[11px]">End must be after start</span>
            )}
          </div>
        </div>

        {isLoading ? (
          <div className="h-36 bg-app-surface-2 rounded animate-pulse" />
        ) : (
          <CalendarHeatmap data={data} selectedDate={selectedDate} onSelectDate={setSelectedDate} />
        )}
      </div>

      {selectedDate && (
        <DayDetail date={selectedDate} onClose={() => setSelectedDate(null)} />
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
