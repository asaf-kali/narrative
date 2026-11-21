import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { NetworkSignal } from '../api/types'
import NetworkView, { CONTROL_CLASS, ContactsOnlyToggle, Toggle } from '../components/NetworkView'
import { boolParam, enumParam, intParam, listParam, stringParam, useUrlState } from '../hooks/useUrlState'

const TIME_RANGES = ['7d', '30d', '90d', '180d', '1y', '2y', '5y', 'all', 'custom'] as const
type TimeRange = (typeof TIME_RANGES)[number]

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

function daysAgo(days: number): string {
  const d = new Date(Date.now() - days * 86_400_000)
  return d.toISOString().slice(0, 10)
}

// Module-level so the hook sees stable references; custom dates default to the 90 days before page load.
const URL_DEFAULTS = {
  signals: GLOBAL_SIGNALS,
  contacts: true,
  me: true,
  nodes: 150,
  range: '90d' as TimeRange,
  from: daysAgo(90),
  to: daysAgo(0),
  backbone: false,
  clusters: 0,  // 0 = let the backend pick
}
const URL_CODECS = {
  signals: listParam(GLOBAL_SIGNALS),
  contacts: boolParam,
  me: boolParam,
  nodes: intParam,
  range: enumParam(TIME_RANGES),
  from: stringParam,
  to: stringParam,
  backbone: boolParam,
  clusters: intParam,
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
  const [url, setUrlState] = useUrlState(URL_DEFAULTS, URL_CODECS)
  const { signals, contacts: contactsOnly, me: includeMe, nodes: maxNodes, range: timeRange, backbone, clusters } = url
  const custom: DateSpan = { from: url.from, to: url.to }

  const span = timeRange === 'custom' ? customSpan(custom) : presetSpan(timeRange)
  const { data, isLoading } = useQuery({
    queryKey: ['global-network', [...signals].sort(), contactsOnly, clusters, includeMe, maxNodes, span.from, span.to],
    queryFn: () => api.globalNetwork(signals, contactsOnly, clusters, includeMe, maxNodes, span.from, span.to),
  })

  const controls = (
    <>
      <select
        value={timeRange}
        onChange={(e) => setUrlState({ range: e.target.value as TimeRange })}
        className={CONTROL_CLASS}
      >
        {TIME_RANGE_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
      </select>
      {timeRange === 'custom' && (
        <span className="flex items-center gap-1 text-xs text-tx-muted">
          <input
            type="date"
            value={custom.from ?? ''}
            max={custom.to}
            onChange={(e) => setUrlState({ from: e.target.value })}
            className={CONTROL_CLASS}
            aria-label="From date"
          />
          –
          <input
            type="date"
            value={custom.to ?? ''}
            min={custom.from}
            onChange={(e) => setUrlState({ to: e.target.value })}
            className={CONTROL_CLASS}
            aria-label="To date"
          />
        </span>
      )}
      <select
        value={maxNodes}
        onChange={(e) => setUrlState({ nodes: Number(e.target.value) })}
        title="Keep the people with the strongest ties"
        className={CONTROL_CLASS}
      >
        {NODE_LIMITS.map((n) => <option key={n} value={n}>Top {n} people</option>)}
      </select>
      <ContactsOnlyToggle checked={contactsOnly} onChange={(next) => setUrlState({ contacts: next })} />
      <Toggle checked={includeMe} onChange={(next) => setUrlState({ me: next })} label="Include me" title="Show yourself and your ties" />
    </>
  )

  return (
    <NetworkView
      data={data}
      isLoading={isLoading}
      availableSignals={GLOBAL_SIGNALS}
      signals={signals}
      onSignalsChange={(next) => setUrlState({ signals: next })}
      backboneOnly={backbone}
      onBackboneOnlyChange={(next) => setUrlState({ backbone: next })}
      clusters={clusters}
      onClustersChange={(next) => setUrlState({ clusters: next })}
      controls={controls}
      showGroups
    />
  )
}
