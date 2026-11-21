import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D, { type ForceGraphMethods, type NodeObject, type LinkObject } from 'react-force-graph-2d'
import type { NetworkEdge, NetworkGraph, NetworkNode, NetworkSignal } from '../api/types'
import { CardSpinner } from './Spinner'

// Distinct palette for community clusters
const CLUSTER_COLORS = [
  '#7c5af6', '#0891b2', '#db2777', '#f59e0b',
  '#84cc16', '#6366f1', '#0d9488', '#f97316',
  '#a78bfa', '#22d3ee', '#fb7185', '#fbbf24',
  '#c084fc', '#34d399', '#f472b6', '#60a5fa',
]

// "Me" stands apart from every community color.
const ME_ID = 'me'
const ME_COLOR = '#f8fafc'

export const SIGNAL_INFO: Record<NetworkSignal, { label: string; hint: string }> = {
  replies: { label: 'Replies', hint: 'Quoting each other\'s messages' },
  reactions: { label: 'Reactions', hint: 'Reacting to each other\'s messages' },
  mentions: { label: 'Mentions', hint: '@mentioning each other' },
  adjacency: { label: 'Back-and-forth', hint: 'Posting right after each other (decays over ~10 min)' },
  groups: { label: 'Shared groups', hint: 'Shared group membership; small groups count more' },
}

const LIST_SIZE = 6
const NODE_SCALE = 5
const MAX_FIT_ZOOM = 2  // small graphs would otherwise zoom in until nodes are huge
const CHARGE_STRENGTH = -120  // d3 default is -30; spread dense groups so labels stay legible
// Repulsion between far-apart nodes only pushes disconnected parts away from each other; cap its range.
const CHARGE_DISTANCE_MAX = 300
const GRAVITY_STRENGTH = 0.05  // weak pull toward the center keeps small disconnected parts near the main one
const FIT_PADDING = 30

/** d3 force pulling every node toward the origin, proportionally to its distance. */
function gravityForce(strength: number) {
  let nodes: NodeObject[] = []
  const force = (alpha: number) => {
    for (const n of nodes) {
      n.vx = (n.vx ?? 0) - (n.x ?? 0) * strength * alpha
      n.vy = (n.vy ?? 0) - (n.y ?? 0) * strength * alpha
    }
  }
  force.initialize = (all: NodeObject[]) => { nodes = all }
  return force
}

function nodeVal(messages: number, maxMessages: number): number {
  return 1 + NODE_SCALE * Math.sqrt(messages / maxMessages)
}

interface GraphNode extends NodeObject, NetworkNode {
  id: string
}

interface GraphLink extends LinkObject {
  source: string | GraphNode
  target: string | GraphNode
  edge: NetworkEdge
}

type Selection =
  | { type: 'node'; id: string }
  | { type: 'edge'; edge: NetworkEdge }
  | null

function clusterColor(cluster: number): string {
  if (cluster < CLUSTER_COLORS.length) return CLUSTER_COLORS[cluster]
  // Past the palette (a manual cluster count), spread hues by the golden angle so neighbors differ.
  return `hsl(${Math.round((cluster * 137.5) % 360)}, 70%, 65%)`
}

function personColor(node: NetworkNode): string {
  if (node.id === ME_ID) return ME_COLOR
  return clusterColor(node.cluster)
}

function touches(edge: NetworkEdge, id: string): boolean {
  return edge.source === id || edge.target === id
}

function other(edge: NetworkEdge, id: string): string {
  return edge.source === id ? edge.target : edge.source
}

function pct(value: number): string {
  return `${Math.round(value * 100)}%`
}

// ── small building blocks ──────────────────────────────────────────────────

function Card({ title, children, className = '' }: { title?: string; children: ReactNode; className?: string }) {
  return (
    <div className={`bg-app-surface border border-app-border rounded-xl p-4 ${className}`}>
      {title && <h3 className="text-[9px] font-semibold text-tx-muted uppercase tracking-widest mb-3">{title}</h3>}
      {children}
    </div>
  )
}

function StatRow({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="flex items-center justify-between gap-3" title={hint}>
      <span className="text-xs text-tx-muted shrink-0">{label}</span>
      <span className="text-xs font-semibold text-tx-secondary tabular-nums text-right">{value}</span>
    </div>
  )
}

function CloseButton({ onClick }: { onClick: () => void }) {
  return (
    <button onClick={onClick} className="text-tx-muted hover:text-tx-secondary text-lg leading-none shrink-0">×</button>
  )
}

function Pill({ active, onClick, title, children }: { active: boolean; onClick: () => void; title?: string; children: ReactNode }) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
        active
          ? 'bg-accent text-white shadow-lg shadow-accent/20'
          : 'bg-app-surface-2 text-tx-secondary hover:text-tx-primary border border-app-border'
      }`}
    >
      {children}
    </button>
  )
}

function GroupList({ groups }: { groups: string[] }) {
  return (
    <div className="space-y-1 max-h-40 overflow-y-auto pr-1">
      {groups.map((g) => (
        <div key={g} className="text-[11px] text-tx-secondary bg-app-surface-2 rounded px-2 py-0.5 truncate">{g}</div>
      ))}
    </div>
  )
}

function PersonDot({ node }: { node: NetworkNode | undefined }) {
  return <div className="w-2 h-2 rounded-full shrink-0" style={{ background: node ? personColor(node) : '#64748b' }} />
}

function PairRow({ edge, nodes, value, onClick }: {
  edge: NetworkEdge; nodes: Map<string, NetworkNode>; value: string; onClick: () => void
}) {
  const a = nodes.get(edge.source)
  const b = nodes.get(edge.target)
  return (
    <button onClick={onClick} className="w-full flex items-center gap-1.5 text-left hover:bg-app-surface-2 rounded px-1 -mx-1 py-0.5">
      <PersonDot node={a} />
      <span className="text-xs text-tx-secondary truncate">{a?.label ?? edge.source}</span>
      <span className="text-[10px] text-tx-muted shrink-0">&</span>
      <span className="text-xs text-tx-secondary truncate">{b?.label ?? edge.target}</span>
      <span className="text-[10px] text-tx-muted ml-auto shrink-0 tabular-nums">{value}</span>
    </button>
  )
}

function PersonRow({ node, value, onClick }: { node: NetworkNode; value: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="w-full flex items-center gap-2 text-left hover:bg-app-surface-2 rounded px-1 -mx-1 py-0.5">
      <PersonDot node={node} />
      <span className="text-xs text-tx-secondary truncate">{node.label}</span>
      <span className="text-[10px] text-tx-muted ml-auto shrink-0 tabular-nums">{value}</span>
    </button>
  )
}

// ── selection panels ───────────────────────────────────────────────────────

function BreakdownBar({ label, value, max, display }: { label: string; value: number; max: number; display: string }) {
  return (
    <div>
      <div className="flex justify-between text-[11px] mb-0.5">
        <span className="text-tx-muted">{label}</span>
        <span className="text-tx-secondary tabular-nums">{display}</span>
      </div>
      <div className="h-1 rounded bg-app-surface-2 overflow-hidden">
        <div className="h-full bg-accent" style={{ width: `${max > 0 ? (value / max) * 100 : 0}%` }} />
      </div>
    </div>
  )
}

function EdgePanel({ edge, nodes, showGroups, onClose }: {
  edge: NetworkEdge; nodes: Map<string, NetworkNode>; showGroups: boolean; onClose: () => void
}) {
  const a = nodes.get(edge.source)
  const b = nodes.get(edge.target)
  const bGroups = new Set(b?.groups ?? [])
  const common = (a?.groups ?? []).filter((g) => bGroups.has(g))
  const parts: { label: string; value: number; display: string }[] = [
    { label: SIGNAL_INFO.replies.label, value: edge.replies, display: edge.replies.toLocaleString() },
    { label: SIGNAL_INFO.reactions.label, value: edge.reactions, display: edge.reactions.toLocaleString() },
    { label: SIGNAL_INFO.mentions.label, value: edge.mentions, display: edge.mentions.toLocaleString() },
    { label: SIGNAL_INFO.adjacency.label, value: edge.adjacency, display: edge.adjacency.toFixed(1) },
  ]
  const max = Math.max(...parts.map((p) => p.value))
  return (
    <Card>
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="text-xs leading-snug">
          <span className="font-semibold text-tx-primary">{a?.label ?? edge.source}</span>
          <span className="text-tx-muted"> & </span>
          <span className="font-semibold text-tx-primary">{b?.label ?? edge.target}</span>
        </div>
        <CloseButton onClick={onClose} />
      </div>
      <div className="space-y-1.5 mb-3">
        <StatRow label="Tie strength" value={edge.weight.toFixed(1)} hint="Weighted sum of the selected signals" />
        <StatRow label="Vs. chance" value={`×${edge.lift.toFixed(1)}`} hint="How much more they interact than their overall activity predicts" />
        <StatRow label="Mutual" value={pct(edge.reciprocity)} hint="0% = one-sided, 100% = both directions equal" />
        {showGroups && <StatRow label="Shared groups" value={edge.shared_groups} />}
        {!edge.backbone && <p className="text-[10px] text-tx-muted">Not on the backbone</p>}
      </div>
      <div className="space-y-2">
        {parts.map((p) => <BreakdownBar key={p.label} label={p.label} value={p.value} max={max} display={p.display} />)}
      </div>
      {showGroups && common.length > 0 && (
        <div className="mt-3">
          <div className="text-[9px] font-semibold text-tx-muted uppercase tracking-widest mb-2">Common groups</div>
          <GroupList groups={common} />
        </div>
      )}
    </Card>
  )
}

function NodePanel({ node, edges, nodes, onSelectEdge, onClose }: {
  node: NetworkNode
  edges: NetworkEdge[]
  nodes: Map<string, NetworkNode>
  onSelectEdge: (edge: NetworkEdge) => void
  onClose: () => void
}) {
  const ties = edges.filter((e) => touches(e, node.id)).sort((x, y) => y.weight - x.weight).slice(0, LIST_SIZE)
  return (
    <Card>
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <div className="text-sm font-semibold text-tx-primary leading-tight">{node.label}</div>
          <div className="text-[10px] text-tx-muted font-mono mt-0.5">{node.id}</div>
        </div>
        <CloseButton onClick={onClose} />
      </div>
      <div className="space-y-1.5 mb-3">
        <StatRow label="Messages" value={node.messages.toLocaleString()} />
        <StatRow label="Total ties" value={node.strength.toFixed(0)} hint="Sum of tie strengths" />
        <StatRow label="Bridging" value={pct(node.bridging)} hint="Share of shortest paths through this person" />
        <StatRow label="Community" value={node.cluster + 1} />
      </div>
      {ties.length > 0 && (
        <div className="mb-3">
          <div className="text-[9px] font-semibold text-tx-muted uppercase tracking-widest mb-2">Closest to</div>
          <div className="space-y-1">
            {ties.map((e) => {
              const peer = nodes.get(other(e, node.id))
              return peer && (
                <PersonRow key={peer.id} node={peer} value={e.weight.toFixed(0)} onClick={() => onSelectEdge(e)} />
              )
            })}
          </div>
        </div>
      )}
      {node.groups.length > 0 && (
        <div>
          <div className="text-[9px] font-semibold text-tx-muted uppercase tracking-widest mb-2">
            Groups ({node.groups.length})
          </div>
          <GroupList groups={node.groups} />
        </div>
      )}
    </Card>
  )
}

// ── main view ──────────────────────────────────────────────────────────────

export interface NetworkViewProps {
  data: NetworkGraph | undefined
  isLoading: boolean
  availableSignals: NetworkSignal[]
  signals: NetworkSignal[]
  onSignalsChange: (signals: NetworkSignal[]) => void
  backboneOnly: boolean
  onBackboneOnlyChange: (backboneOnly: boolean) => void
  clusters: number  // 0 = automatic
  onClustersChange: (clusters: number) => void
  controls?: ReactNode
  showGroups?: boolean
}

export default function NetworkView({
  data, isLoading, availableSignals, signals, onSignalsChange, backboneOnly, onBackboneOnlyChange,
  clusters, onClustersChange, controls, showGroups = false,
}: NetworkViewProps) {
  const [selection, setSelection] = useState<Selection>(null)

  // New data (signals, filters) invalidates the selection and re-fits the view once the layout settles.
  const needsFit = useRef(true)
  useEffect(() => {
    setSelection(null)
    needsFit.current = true
  }, [data])

  const containerRef = useRef<HTMLDivElement>(null)
  const [dims, setDims] = useState({ width: 800, height: 500 })
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const obs = new ResizeObserver(([entry]) => {
      setDims({ width: entry.contentRect.width, height: entry.contentRect.height })
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  const fgRef = useRef<ForceGraphMethods<GraphNode, GraphLink>>()

  const edges = useMemo(() => data?.edges ?? [], [data])
  const nodeById = useMemo(() => new Map((data?.nodes ?? []).map((n) => [n.id, n])), [data])

  const visibleEdges = useMemo(() => (backboneOnly ? edges.filter((e) => e.backbone) : edges), [edges, backboneOnly])
  const maxWeight = useMemo(() => Math.max(1, ...edges.map((e) => e.weight)), [edges])
  const maxMessages = useMemo(() => Math.max(1, ...(data?.nodes ?? []).map((n) => n.messages)), [data])

  // Refetches (e.g. a new cluster count) start each person where they were, so the layout doesn't jump.
  const prevNodes = useRef<GraphNode[]>([])
  const graphData = useMemo(() => {
    const prev = new Map(prevNodes.current.map((n) => [n.id, n]))
    const nodes = (data?.nodes ?? []).map((n) => {
      const p = prev.get(n.id)
      return p?.x !== undefined && p.y !== undefined ? { ...n, x: p.x, y: p.y } : { ...n }
    }) as GraphNode[]
    const links = visibleEdges.map((e) => ({ source: e.source, target: e.target, edge: e })) as GraphLink[]
    return { nodes, links }
  }, [data, visibleEdges])
  useEffect(() => { prevNodes.current = graphData.nodes }, [graphData])

  useEffect(() => {
    const fg = fgRef.current
    if (!fg) return
    fg.d3Force('charge')?.strength(CHARGE_STRENGTH).distanceMax(CHARGE_DISTANCE_MAX)
    fg.d3Force('gravity', gravityForce(GRAVITY_STRENGTH))
  }, [graphData])

  // Keep the whole graph in view while the layout settles, until the user zooms, pans or drags.
  const fitView = useCallback((durationMs: number) => {
    const fg = fgRef.current
    if (!fg) return
    fg.zoomToFit(durationMs, FIT_PADDING)
    if (fg.zoom() > MAX_FIT_ZOOM) fg.zoom(MAX_FIT_ZOOM, durationMs)
  }, [])
  const stopAutoFit = useCallback(() => { needsFit.current = false }, [])

  const strongest = useMemo(() => [...edges].sort((a, b) => b.weight - a.weight).slice(0, LIST_SIZE), [edges])
  // Lift is noisy on tiny ties: rank only ties at least as strong as the median.
  const surprising = useMemo(() => {
    const weights = edges.map((e) => e.weight).sort((a, b) => a - b)
    const median = weights[Math.floor(weights.length / 2)] ?? 0
    return edges.filter((e) => e.lift > 1 && e.weight >= median).sort((a, b) => b.lift - a.lift).slice(0, LIST_SIZE)
  }, [edges])
  const bridges = useMemo(
    () => [...(data?.nodes ?? [])].filter((n) => n.bridging > 0).sort((a, b) => b.bridging - a.bridging).slice(0, LIST_SIZE),
    [data],
  )

  const selectedId = selection?.type === 'node' ? selection.id : null
  const selectedEdge = selection?.type === 'edge' ? selection.edge : null
  // The selected person plus everyone they're tied to; other nodes are dimmed.
  const focusIds = useMemo(() => {
    if (!selectedId) return null
    return new Set([selectedId, ...edges.filter((e) => touches(e, selectedId)).map((e) => other(e, selectedId))])
  }, [edges, selectedId])

  const isHighlighted = useCallback((edge: NetworkEdge) => {
    if (selectedId) return touches(edge, selectedId)
    if (selectedEdge) return edge === selectedEdge
    return false
  }, [selectedId, selectedEdge])

  const linkColor = useCallback((l: LinkObject) => {
    const edge = (l as GraphLink).edge
    if (isHighlighted(edge)) return 'rgba(167,139,250,0.85)'
    if (selection) return 'rgba(255,255,255,0.03)'
    return edge.backbone ? 'rgba(255,255,255,0.22)' : 'rgba(255,255,255,0.07)'
  }, [isHighlighted, selection])

  const toggleSignal = (signal: NetworkSignal) => {
    const next = signals.includes(signal) ? signals.filter((s) => s !== signal) : [...signals, signal]
    if (next.length > 0) onSignalsChange(next)
  }

  const focusNode = (id: string) => {
    setSelection({ type: 'node', id })
    const n = graphData.nodes.find((g) => g.id === id)
    if (n?.x !== undefined && n.y !== undefined) {
      fgRef.current?.centerAt(n.x, n.y, 500)
      fgRef.current?.zoom(2.5, 500)
    }
  }

  const selectedNode = selectedId ? nodeById.get(selectedId) : undefined

  return (
    <div className="flex gap-4 h-full min-h-0">
      {/* Graph panel */}
      <div className="flex-1 flex flex-col bg-app-surface border border-app-border rounded-xl overflow-hidden min-w-0">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-2.5 border-b border-app-border shrink-0">
          <div className="flex flex-wrap gap-1">
            {availableSignals.map((s) => (
              <Pill key={s} active={signals.includes(s)} onClick={() => toggleSignal(s)} title={SIGNAL_INFO[s].hint}>
                {SIGNAL_INFO[s].label}
              </Pill>
            ))}
          </div>
          {controls}
          {data && data.nodes.length > 0 && (
            <ClustersControl
              value={clusters || data.communities}
              isAuto={clusters === 0}
              max={data.nodes.length}
              onChange={onClustersChange}
            />
          )}
          <label className="flex items-center gap-1.5 cursor-pointer select-none ml-auto" title="Hide ties that are weak relative to both people's other ties">
            <input
              type="checkbox"
              checked={backboneOnly}
              onChange={(e) => onBackboneOnlyChange(e.target.checked)}
              className="w-3 h-3 accent-accent"
            />
            <span className="text-xs text-tx-secondary">Strongest ties only</span>
          </label>
          <button
            onClick={() => fgRef.current?.zoomToFit(400, 20)}
            className="text-[10px] text-tx-muted hover:text-tx-secondary transition-colors"
          >
            Fit
          </button>
        </div>

        <div ref={containerRef} className="flex-1 min-h-0" onPointerDown={stopAutoFit} onWheel={stopAutoFit}>
          {isLoading ? (
            <CardSpinner className="h-full" />
          ) : graphData.nodes.length === 0 ? (
            <div className="h-full flex items-center justify-center text-tx-muted text-sm">
              No interactions found — try more signals or a wider time range.
            </div>
          ) : (
            <ForceGraph2D
              ref={fgRef}
              graphData={graphData}
              width={dims.width}
              height={dims.height}
              backgroundColor="#0d0f17"
              nodeLabel={(n) => `${(n as GraphNode).label} · ${(n as GraphNode).messages.toLocaleString()} msgs`}
              nodeColor={(n) => {
                const node = n as GraphNode
                const dim = focusIds !== null && !focusIds.has(node.id)
                return dim ? 'rgba(100,116,139,0.35)' : personColor(node)
              }}
              nodeVal={(n) => nodeVal((n as GraphNode).messages, maxMessages)}
              linkColor={linkColor}
              linkWidth={(l) => 0.4 + 3 * Math.sqrt((l as GraphLink).edge.weight / maxWeight)}
              onNodeClick={(n) => focusNode((n as GraphNode).id)}
              onLinkClick={(l) => setSelection({ type: 'edge', edge: (l as GraphLink).edge })}
              onBackgroundClick={() => setSelection(null)}
              cooldownTicks={150}
              onEngineTick={() => {
                if (needsFit.current) fitView(0)
              }}
              onEngineStop={() => {
                if (!needsFit.current) return
                needsFit.current = false
                fitView(300)
              }}
              nodeCanvasObjectMode={() => 'after'}
              nodeCanvasObject={(node, ctx, globalScale) => {
                const n = node as GraphNode
                if (globalScale < 1.5 && n.id !== selectedId && n.id !== ME_ID) return
                const radius = Math.sqrt(nodeVal(n.messages, maxMessages)) * 4  // force-graph's default nodeRelSize
                const fontSize = 10 / globalScale
                ctx.font = `${fontSize}px sans-serif`
                ctx.fillStyle = 'rgba(226,232,240,0.85)'
                ctx.textAlign = 'center'
                ctx.textBaseline = 'top'
                ctx.fillText(n.label.split(' ')[0], node.x ?? 0, (node.y ?? 0) + radius + 1)
              }}
            />
          )}
        </div>
      </div>

      {/* Sidebar */}
      <div className="w-60 shrink-0 flex flex-col gap-3 overflow-y-auto">
        <Card title="Stats" className="space-y-1.5 shrink-0">
          <StatRow label="People" value={(data?.nodes.length ?? 0).toLocaleString()} />
          <StatRow label="Ties shown" value={`${visibleEdges.length.toLocaleString()} / ${edges.length.toLocaleString()}`} />
          <StatRow label="Communities" value={data?.communities ?? 0} />
        </Card>

        {selectedEdge && (
          <EdgePanel edge={selectedEdge} nodes={nodeById} showGroups={showGroups} onClose={() => setSelection(null)} />
        )}
        {selectedNode && (
          <NodePanel
            node={selectedNode}
            edges={edges}
            nodes={nodeById}
            onSelectEdge={(edge) => setSelection({ type: 'edge', edge })}
            onClose={() => setSelection(null)}
          />
        )}

        {!selection && (
          <>
            <Card title="Strongest ties" className="shrink-0">
              <div className="space-y-1">
                {strongest.map((e) => (
                  <PairRow key={`${e.source}|${e.target}`} edge={e} nodes={nodeById} value={e.weight.toFixed(0)}
                    onClick={() => setSelection({ type: 'edge', edge: e })} />
                ))}
              </div>
            </Card>
            {surprising.length > 0 && (
              <Card title="Closer than chance" className="shrink-0">
                <div className="space-y-1">
                  {surprising.map((e) => (
                    <PairRow key={`${e.source}|${e.target}`} edge={e} nodes={nodeById} value={`×${e.lift.toFixed(1)}`}
                      onClick={() => setSelection({ type: 'edge', edge: e })} />
                  ))}
                </div>
              </Card>
            )}
            {bridges.length > 0 && (
              <Card title="Bridges" className="shrink-0">
                <div className="space-y-1">
                  {bridges.map((n) => (
                    <PersonRow key={n.id} node={n} value={pct(n.bridging)} onClick={() => focusNode(n.id)} />
                  ))}
                </div>
              </Card>
            )}
            <p className="text-[10px] text-tx-muted px-1">Click a person or a tie for details.</p>
          </>
        )}
      </div>
    </div>
  )
}

const CLUSTERS_DEBOUNCE_MS = 400

/** Number of communities: shows the automatic pick until the user sets one; "Auto" goes back. */
function ClustersControl({ value, isAuto, max, onChange }: {
  value: number
  isAuto: boolean
  max: number
  onChange: (clusters: number) => void
}) {
  const [draft, setDraft] = useState(String(value))
  useEffect(() => setDraft(String(value)), [value])

  // Typing "12" shouldn't fetch for "1" first.
  useEffect(() => {
    const n = Number(draft)
    if (!Number.isInteger(n) || n < 1 || n === value) return
    const timer = setTimeout(() => onChange(Math.min(n, max)), CLUSTERS_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [draft, value, max, onChange])

  return (
    <label className="flex items-center gap-1.5 text-xs text-tx-secondary" title="Number of communities (colors)">
      Clusters
      <input
        type="number"
        min={1}
        max={max}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        className="w-12 bg-app-surface-2 border border-app-border rounded-full px-2 py-0.5 text-xs text-tx-secondary"
      />
      {isAuto ? (
        <span className="text-[10px] text-tx-muted">auto</span>
      ) : (
        <button onClick={() => onChange(0)} className="text-[10px] text-tx-muted hover:text-tx-secondary transition-colors">
          Auto
        </button>
      )}
    </label>
  )
}

export function ContactsOnlyToggle({ checked, onChange }: { checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="flex items-center gap-1.5 cursor-pointer select-none" title="Hide people who aren't saved in your contacts">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="w-3 h-3 accent-accent" />
      <span className="text-xs text-tx-secondary">Contacts only</span>
    </label>
  )
}
