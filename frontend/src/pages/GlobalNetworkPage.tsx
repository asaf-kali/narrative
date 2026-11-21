import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { NetworkSignal } from '../api/types'
import NetworkView, { ContactsOnlyToggle } from '../components/NetworkView'

type TimeRange = '7d' | '30d' | '90d' | '180d' | '1y' | '2y' | '5y' | 'all' | 'custom'

interface DateSpan {
  from?: string
  to?: string
}

const GLOBAL_SIGNALS: NetworkSignal[] = ['replies', 'reactions', 'mentions', 'adjacency', 'groups']
const NODE_LIMITS = [50, 100, 150, 300]

const TIME_RANGE_OPTIONS: { value: TimeRange; label: string; days?: number }[] = [
  { value: '7d', label: '7 days', days: 7 },
  { value: '30d', label: '30 days', days: 30 },
  { value: '90d', label: '90 days', days: 90 },
  { value: '180d', label: '180 days', days: 180 },
  { value: '1y', label: '1 year', days: 365 },
  { value: '2y', label: '2 years', days: 730 },
  { value: '5y', label: '5 years', days: 1826 },
  { value: 'all', label: 'All time' },
  { value: 'custom', label: 'Custom…' },
]

const DATE_INPUT_CLASS = 'bg-app-surface-2 border border-app-border rounded-full px-2.5 py-0.5 text-xs text-tx-secondary'

function daysAgo(days: number): string {
  const d = new Date(Date.now() - days * 86_400_000)
  return d.toISOString().slice(0, 10)
}

function presetSpan(range: TimeRange): DateSpan {
  const days = TIME_RANGE_OPTIONS.find((opt) => opt.value === range)?.days
  return days === undefined ? {} : { from: daysAgo(days) }
}

function customSpan(custom: DateSpan): DateSpan {
  // The API compares datetimes, so a bare end date would exclude that day's messages.
  return { from: custom.from || undefined, to: custom.to ? `${custom.to}T23:59:59` : undefined }
}

export default function GlobalNetworkPage() {
  const [signals, setSignals] = useState<NetworkSignal[]>(GLOBAL_SIGNALS)
  const [contactsOnly, setContactsOnly] = useState(true)
  const [includeMe, setIncludeMe] = useState(true)
  const [maxNodes, setMaxNodes] = useState(150)
  const [timeRange, setTimeRange] = useState<TimeRange>('90d')
  const [custom, setCustom] = useState<DateSpan>({ from: daysAgo(90), to: daysAgo(0) })

  const span = timeRange === 'custom' ? customSpan(custom) : presetSpan(timeRange)
  const { data, isLoading } = useQuery({
    queryKey: ['global-network', [...signals].sort(), contactsOnly, includeMe, maxNodes, span.from, span.to],
    queryFn: () => api.globalNetwork(signals, contactsOnly, includeMe, maxNodes, span.from, span.to),
  })

  const controls = (
    <>
      <select
        value={timeRange}
        onChange={(e) => setTimeRange(e.target.value as TimeRange)}
        className="bg-app-surface-2 border border-app-border rounded-full px-2.5 py-1 text-xs text-tx-secondary"
      >
        {TIME_RANGE_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
      </select>
      {timeRange === 'custom' && (
        <span className="flex items-center gap-1 text-xs text-tx-muted">
          <input
            type="date"
            value={custom.from ?? ''}
            max={custom.to}
            onChange={(e) => setCustom({ ...custom, from: e.target.value })}
            className={DATE_INPUT_CLASS}
            aria-label="From date"
          />
          –
          <input
            type="date"
            value={custom.to ?? ''}
            min={custom.from}
            onChange={(e) => setCustom({ ...custom, to: e.target.value })}
            className={DATE_INPUT_CLASS}
            aria-label="To date"
          />
        </span>
      )}
      <select
        value={maxNodes}
        onChange={(e) => setMaxNodes(Number(e.target.value))}
        title="Keep the people with the strongest ties"
        className="bg-app-surface-2 border border-app-border rounded-full px-2.5 py-1 text-xs text-tx-secondary"
      >
        {NODE_LIMITS.map((n) => <option key={n} value={n}>Top {n} people</option>)}
      </select>
      <ContactsOnlyToggle checked={contactsOnly} onChange={setContactsOnly} />
      <label className="flex items-center gap-1.5 cursor-pointer select-none">
        <input type="checkbox" checked={includeMe} onChange={(e) => setIncludeMe(e.target.checked)} className="w-3 h-3 accent-accent" />
        <span className="text-xs text-tx-secondary">Include me</span>
      </label>
    </>
  )

  return (
    <NetworkView
      data={data}
      isLoading={isLoading}
      availableSignals={GLOBAL_SIGNALS}
      signals={signals}
      onSignalsChange={setSignals}
      controls={controls}
      showGroups
    />
  )
}
