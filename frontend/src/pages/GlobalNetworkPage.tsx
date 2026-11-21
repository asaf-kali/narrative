import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { NetworkSignal } from '../api/types'
import NetworkView from '../components/NetworkView'

type TimeRange = '7d' | '30d' | '90d' | 'all'

const GLOBAL_SIGNALS: NetworkSignal[] = ['replies', 'reactions', 'mentions', 'adjacency', 'groups']
const NODE_LIMITS = [50, 100, 150, 300]

const TIME_RANGE_OPTIONS: { value: TimeRange; label: string }[] = [
  { value: '7d', label: '7 days' },
  { value: '30d', label: '30 days' },
  { value: '90d', label: '90 days' },
  { value: 'all', label: 'All time' },
]

function dateFrom(range: TimeRange): string | undefined {
  if (range === 'all') return undefined
  const days = range === '7d' ? 7 : range === '30d' ? 30 : 90
  const d = new Date(Date.now() - days * 86_400_000)
  return d.toISOString().slice(0, 10)
}

export default function GlobalNetworkPage() {
  const [signals, setSignals] = useState<NetworkSignal[]>(GLOBAL_SIGNALS)
  const [includeMe, setIncludeMe] = useState(false)
  const [maxNodes, setMaxNodes] = useState(150)
  const [timeRange, setTimeRange] = useState<TimeRange>('90d')

  const { data, isLoading } = useQuery({
    queryKey: ['global-network', [...signals].sort(), includeMe, maxNodes, timeRange],
    queryFn: () => api.globalNetwork(signals, includeMe, maxNodes, dateFrom(timeRange)),
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
      <select
        value={maxNodes}
        onChange={(e) => setMaxNodes(Number(e.target.value))}
        title="Keep the people with the strongest ties"
        className="bg-app-surface-2 border border-app-border rounded-full px-2.5 py-1 text-xs text-tx-secondary"
      >
        {NODE_LIMITS.map((n) => <option key={n} value={n}>Top {n} people</option>)}
      </select>
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
