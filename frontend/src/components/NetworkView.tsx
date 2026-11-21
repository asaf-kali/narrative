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

export const SIGNAL_INFO: Record<NetworkSignal, { label: string; hint: string }> = {
  replies: { label: 'Replies', hint: 'Quoting each other\'s messages' },
  reactions: { label: 'Reactions', hint: 'Reacting to each other\'s messages' },
  mentions: { label: 'Mentions', hint: '@mentioning each other' },
  adjacency: { label: 'Back-and-forth', hint: 'Posting right after each other (decays over ~10 min)' },
  groups: { label: 'Shared groups', hint: 'Shared group membership; small groups count more' },
}

// Show only the backbone by default once the full graph gets busy.
const BACKBONE_DEFAULT_EDGES = 200
const LIST_SIZE = 6
const NODE_SCALE = 5
const MAX_FIT_ZOOM = 2  // small graphs would otherwise zoom in until nodes are huge
const CHARGE_STRENGTH = -120  // d3 default is -30; spread dense groups so labels stay legible

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
  return CLUSTER_COLORS[cluster % CLUSTER_COLORS.length]
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
  return <div className="w-2 h-2 rounded-full shrink-0" style={{ background: node ? clusterColor(node.cluster) : '#64748b' }} />
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
  controls?: ReactNode
  showGroups?: boolean
}

export default function NetworkView({
  data, isLoading, availableSignals, signals, onSignalsChange, controls, showGroups = false,
}: NetworkViewProps) {
  const [backboneOverride, setBackboneOverride] = useState<boolean | null>(null)
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
  const backboneOnly = backboneOverride ?? edges.length > BACKBONE_DEFAULT_EDGES

  const visibleEdges = useMemo(() => (backboneOnly ? edges.filter((e) => e.backbone) : edges), [edges, backboneOnly])
  const maxWeight = useMemo(() => Math.max(1, ...edges.map((e) => e.weight)), [edges])
  const maxMessages = useMemo(() => Math.max(1, ...(data?.nodes ?? []).map((n) => n.messages)), [data])

  const graphData = useMemo(() => ({
    nodes: (data?.nodes ?? []).map((n) => ({ ...n })) as GraphNode[],
    links: visibleEdges.map((e) => ({ source: e.source, target: e.target, edge: e })) as GraphLink[],
  }), [data, visibleEdges])

  useEffect(() => {
    fgRef.current?.d3Force('charge')?.strength(CHARGE_STRENGTH)
  }, [graphData])

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
          <label className="flex items-center gap-1.5 cursor-pointer select-none ml-auto" title="Hide ties that are weak relative to both people's other ties">
            <input
              type="checkbox"
              checked={backboneOnly}
              onChange={(e) => setBackboneOverride(e.target.checked)}
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

        <div ref={containerRef} className="flex-1 min-h-0">
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
                return dim ? 'rgba(100,116,139,0.35)' : clusterColor(node.cluster)
              }}
              nodeVal={(n) => nodeVal((n as GraphNode).messages, maxMessages)}
              linkColor={linkColor}
              linkWidth={(l) => 0.4 + 3 * Math.sqrt((l as GraphLink).edge.weight / maxWeight)}
              onNodeClick={(n) => focusNode((n as GraphNode).id)}
              onLinkClick={(l) => setSelection({ type: 'edge', edge: (l as GraphLink).edge })}
              onBackgroundClick={() => setSelection(null)}
              cooldownTicks={150}
              onEngineStop={() => {
                if (!needsFit.current) return
                needsFit.current = false
                const fg = fgRef.current
                if (!fg) return
                fg.zoomToFit(0, 30)
                if (fg.zoom() > MAX_FIT_ZOOM) fg.zoom(MAX_FIT_ZOOM)
              }}
              nodeCanvasObjectMode={() => 'after'}
              nodeCanvasObject={(node, ctx, globalScale) => {
                const n = node as GraphNode
                if (globalScale < 1.5 && n.id !== selectedId) return
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
