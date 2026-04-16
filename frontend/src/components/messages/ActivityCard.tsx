import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { CHAT_COLORS } from '../MessageFeed'

// ── constants ─────────────────────────────────────────────────────────────────

const OTHER_COLOR = '#374061'
const TOOLTIP_STYLE = { background: '#0d0f17', border: '1px solid #1a1d2e', color: '#e2e8f0', borderRadius: 8, fontSize: 12 }
const TICK_STYLE = { fill: '#64748b', fontSize: 10 }

// ── types & helpers ───────────────────────────────────────────────────────────

export type TimelineRow = { bucket: string } & Record<string, number | string>

/** Build chart rows from raw timeline buckets. Pass `allBuckets` to ensure empty buckets are included. */
export function buildTimelineRows(
  timeline: { bucket: string; chat_name: string; count: number }[],
  topChats: string[],
  allBuckets?: string[],
): TimelineRow[] {
  const topSet = new Set(topChats)
  const map = new Map<string, TimelineRow>()
  if (allBuckets) {
    for (const b of allBuckets) map.set(b, { bucket: b })
  }
  for (const b of timeline) {
    if (!map.has(b.bucket)) map.set(b.bucket, { bucket: b.bucket })
    const row = map.get(b.bucket)!
    const key = topSet.has(b.chat_name) ? b.chat_name : 'Other'
    row[key] = ((row[key] as number | undefined) ?? 0) + b.count
  }
  return [...map.values()]
}

function shortName(name: string, max = 22): string {
  return name.length > max ? name.slice(0, max - 1) + '…' : name
}

// ── component ─────────────────────────────────────────────────────────────────

interface Props {
  rows: TimelineRow[]
  barKeys: string[]
  colorMap: Map<string, string>
  label?: string
  height?: number
  tickFormatter?: (v: string) => string
  tickInterval?: number | 'preserveStart' | 'preserveEnd' | 'preserveStartEnd' | 'equidistantPreserveStart'
}

export default function ActivityCard({
  rows,
  barKeys,
  colorMap,
  label = 'Activity',
  height = 160,
  tickFormatter = (v: string) => v,
  tickInterval = 'preserveStartEnd',
}: Props) {
  return (
    <div className="bg-app-surface border border-app-border rounded-xl p-4">
      <p className="text-[10px] font-semibold text-tx-muted uppercase tracking-widest mb-2">{label}</p>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={rows} barCategoryGap="10%">
          <XAxis
            dataKey="bucket"
            tick={TICK_STYLE}
            interval={tickInterval}
            tickFormatter={tickFormatter}
          />
          <YAxis tick={TICK_STYLE} width={28} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} formatter={(v: string) => shortName(v)} />
          {barKeys.map((key, i) => (
            <Bar
              key={key}
              dataKey={key}
              stackId="a"
              fill={key === 'Other' ? OTHER_COLOR : (colorMap.get(key) ?? CHAT_COLORS[i % CHAT_COLORS.length])}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
