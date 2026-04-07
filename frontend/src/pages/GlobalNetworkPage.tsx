import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import ForceGraph2D, { type ForceGraphMethods, type NodeObject, type LinkObject } from 'react-force-graph-2d'
import { api } from '../api/client'
import type { NetworkNode } from '../api/types'

const CLUSTER_COLORS = [
  '#7c5af6', '#0891b2', '#db2777', '#f59e0b',
  '#84cc16', '#6366f1', '#0d9488', '#f97316',
  '#a78bfa', '#22d3ee', '#fb7185', '#fbbf24',
  '#c084fc', '#34d399', '#f472b6', '#60a5fa',
]

type Mode = 'coactivity' | 'reactions'

interface GraphNode extends NodeObject {
  id: string; label: string; messages: number
  cluster: number; centrality: number; groups: string[]
}
interface GraphLink extends LinkObject {
  source: string | GraphNode; target: string | GraphNode; weight: number
}

function clusterColor(cluster: number) {
  return CLUSTER_COLORS[cluster % CLUSTER_COLORS.length]
}

function sharedGroups(a: NetworkNode | undefined, b: NetworkNode | undefined): string[] {
  if (!a || !b) return []
  const bs = new Set(b.groups)
  return a.groups.filter((g) => bs.has(g))
}

// ── sub-components ─────────────────────────────────────────────────────────

function StatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-xs text-slate-500 shrink-0">{label}</span>
      <span className="text-xs font-semibold text-slate-300 tabular-nums text-right">{value}</span>
    </div>
  )
}

function NodePanel({ node, onClose }: { node: NetworkNode; onClose: () => void }) {
  return (
    <div className="bg-app-surface border border-app-border rounded-xl p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-sm font-semibold text-slate-100 leading-tight">{node.label}</div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">{node.id}</div>
        </div>
        <button onClick={onClose} className="text-slate-600 hover:text-slate-400 text-lg leading-none mt-0.5">×</button>
      </div>

      <div className="space-y-1.5">
        <StatRow label="Messages" value={node.messages.toLocaleString()} />
        <StatRow label="Centrality" value={`${(node.centrality * 100).toFixed(1)}%`} />
        <StatRow label="Community" value={node.cluster} />
      </div>

      {node.groups.length > 0 && (
        <div>
          <div className="text-[9px] font-semibold text-slate-500 uppercase tracking-widest mb-2">
            Groups ({node.groups.length})
          </div>
          <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
            {node.groups.map((g) => (
              <div key={g} className="text-[11px] text-slate-400 bg-app-surface-2 rounded px-2 py-0.5 truncate">{g}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function EdgePanel({ shared, labelA, labelB, weight, onClose }: {
  shared: string[]; labelA: string; labelB: string; weight: number; onClose: () => void
}) {
  return (
    <div className="bg-app-surface border border-app-border rounded-xl p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="text-xs text-slate-300 leading-snug">
          <span className="font-semibold text-slate-100">{labelA}</span>
          <span className="text-slate-500"> & </span>
          <span className="font-semibold text-slate-100">{labelB}</span>
        </div>
        <button onClick={onClose} className="text-slate-600 hover:text-slate-400 text-lg leading-none shrink-0">×</button>
      </div>
      <StatRow label="Shared groups" value={weight} />
      <div>
        <div className="text-[9px] font-semibold text-slate-500 uppercase tracking-widest mb-2">Common groups</div>
        <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
          {shared.map((g) => (
            <div key={g} className="text-[11px] text-slate-400 bg-app-surface-2 rounded px-2 py-0.5 truncate">{g}</div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── main page ──────────────────────────────────────────────────────────────

type Selection =
  | { type: 'node'; node: NetworkNode }
  | { type: 'edge'; nodeA: NetworkNode; nodeB: NetworkNode; weight: number }
  | null

export default function GlobalNetworkPage() {
  const [mode, setMode] = useState<Mode>('coactivity')
  const [includeMe, setIncludeMe] = useState(false)
  const [minWeight, setMinWeight] = useState(2)
  const [selection, setSelection] = useState<Selection>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['global-network', mode, includeMe],
    queryFn: () => api.globalNetwork(mode, includeMe),
  })

  // Container sizing
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

  // Build node lookup for click handlers
  const nodeById = useMemo<Map<string, NetworkNode>>(() => {
    const map = new Map<string, NetworkNode>()
    data?.nodes.forEach((n) => map.set(n.id, n))
    return map
  }, [data])

  const maxWeight = useMemo(() => Math.max(2, ...(data?.edges.map((e) => e.weight) ?? [2])), [data])

  const graphData = useMemo(() => {
    if (!data) return { nodes: [], links: [] }
    const visibleLinks = data.edges.filter((e) => e.weight >= minWeight)
    const visibleIds = new Set(visibleLinks.flatMap((e) => [e.source, e.target]))
    return {
      nodes: data.nodes.filter((n) => visibleIds.has(n.id)) as GraphNode[],
      links: visibleLinks.map((e) => ({ source: e.source, target: e.target, weight: e.weight })) as GraphLink[],
    }
  }, [data, minWeight])

  const topNodes = useMemo(
    () => [...(data?.nodes ?? [])].sort((a, b) => b.centrality - a.centrality).slice(0, 7),
    [data],
  )

  const handleNodeClick = useCallback((n: GraphNode) => {
    const node = nodeById.get(n.id)
    if (!node) return
    setSelection({ type: 'node', node })
    fgRef.current?.centerAt(n.x, n.y, 500)
    fgRef.current?.zoom(3, 500)
  }, [nodeById])

  const handleLinkClick = useCallback((link: GraphLink) => {
    const srcId = typeof link.source === 'string' ? link.source : link.source.id
    const dstId = typeof link.target === 'string' ? link.target : link.target.id
    const nodeA = nodeById.get(srcId)
    const nodeB = nodeById.get(dstId)
    if (!nodeA || !nodeB) return
    setSelection({ type: 'edge', nodeA, nodeB, weight: link.weight })
  }, [nodeById])

  return (
    <div className="flex gap-4 h-full min-h-0">
      {/* Graph panel */}
      <div className="flex-1 flex flex-col bg-app-surface border border-app-border rounded-xl overflow-hidden min-w-0">
        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3 px-4 py-2.5 border-b border-app-border shrink-0">
          <div className="flex gap-1">
            {(['coactivity', 'reactions'] as Mode[]).map((m) => (
              <button key={m} onClick={() => { setMode(m); setMinWeight(m === 'coactivity' ? 2 : 1); setSelection(null) }}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${mode === m
                  ? 'bg-accent text-white shadow-lg shadow-accent/20'
                  : 'bg-app-surface-2 text-slate-400 hover:text-slate-200 border border-app-border'}`}>
                {m === 'coactivity' ? 'Shared groups' : 'Reactions'}
              </button>
            ))}
          </div>

          <label className="flex items-center gap-1.5 cursor-pointer select-none ml-1">
            <input type="checkbox" checked={includeMe} onChange={(e) => { setIncludeMe(e.target.checked); setSelection(null) }}
              className="w-3 h-3 accent-accent" />
            <span className="text-xs text-slate-400">Include me</span>
          </label>

          <div className="flex items-center gap-2 ml-auto">
            <span className="text-xs text-slate-500">Min. shared groups</span>
            <input type="range" min={1} max={Math.min(maxWeight, 20)} value={minWeight}
              onChange={(e) => setMinWeight(Number(e.target.value))} className="w-28 accent-accent" />
            <span className="text-xs text-slate-300 tabular-nums w-4 text-right">{minWeight}</span>
          </div>

          <button onClick={() => fgRef.current?.zoomToFit(400, 20)}
            className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors">
            Fit
          </button>
        </div>

        {/* Canvas */}
        <div ref={containerRef} className="flex-1 min-h-0">
          {isLoading ? (
            <div className="h-full bg-app-surface-2 animate-pulse" />
          ) : graphData.nodes.length === 0 ? (
            <div className="h-full flex items-center justify-center text-slate-500 text-sm">
              No data — lower the min. shared groups slider.
            </div>
          ) : (
            <ForceGraph2D
              ref={fgRef}
              graphData={graphData}
              width={dims.width}
              height={dims.height}
              backgroundColor="#0d0f17"
              nodeLabel={(n) => `${(n as GraphNode).label} · ${(n as GraphNode).groups.length} groups`}
              nodeColor={(n) => clusterColor((n as GraphNode).cluster)}
              nodeVal={(n) => Math.max(1, Math.sqrt((n as GraphNode).messages / 100))}
              linkColor={() => 'rgba(255,255,255,0.05)'}
              linkWidth={(l) => Math.log1p((l as GraphLink).weight) * 0.5}
              linkDirectionalArrowLength={mode === 'reactions' ? 4 : 0}
              linkDirectionalArrowRelPos={1}
              onNodeClick={(n) => handleNodeClick(n as GraphNode)}
              onLinkClick={(l) => handleLinkClick(l as GraphLink)}
              nodeCanvasObjectMode={() => 'after'}
              nodeCanvasObject={(node, ctx, globalScale) => {
                const n = node as GraphNode
                if (globalScale < 2) return
                const label = n.label.split(' ')[0]
                const fontSize = 10 / globalScale
                ctx.font = `${fontSize}px sans-serif`
                ctx.fillStyle = 'rgba(226,232,240,0.85)'
                ctx.textAlign = 'center'
                ctx.textBaseline = 'top'
                ctx.fillText(label, node.x ?? 0, (node.y ?? 0) + Math.sqrt(n.messages / 100) + 2)
              }}
            />
          )}
        </div>
      </div>

      {/* Sidebar */}
      <div className="w-52 shrink-0 flex flex-col gap-3 overflow-y-auto">
        <div className="bg-app-surface border border-app-border rounded-xl p-4 space-y-1.5 shrink-0">
          <h3 className="text-[9px] font-semibold text-slate-500 uppercase tracking-widest mb-3">Stats</h3>
          <StatRow label="Contacts" value={data?.nodes.length.toLocaleString() ?? '—'} />
          <StatRow label="Visible" value={graphData.nodes.length.toLocaleString()} />
          <StatRow label="Connections" value={graphData.links.length.toLocaleString()} />
          <StatRow label="Communities" value={data?.communities ?? '—'} />
        </div>

        {selection && (
          selection.type === 'node'
            ? <NodePanel node={selection.node} onClose={() => setSelection(null)} />
            : <EdgePanel
                nodeA={selection.nodeA} nodeB={selection.nodeB}
                labelA={selection.nodeA.label} labelB={selection.nodeB.label}
                weight={selection.weight}
                shared={sharedGroups(selection.nodeA, selection.nodeB)}
                onClose={() => setSelection(null)}
              />
        )}

        {!selection && (
          <div className="bg-app-surface border border-app-border rounded-xl p-4 flex-1">
            <h3 className="text-[9px] font-semibold text-slate-500 uppercase tracking-widest mb-3">Most Connected</h3>
            <div className="space-y-2.5">
              {topNodes.map((node, i) => (
                <div key={node.id} className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-600 w-3 shrink-0">{i + 1}</span>
                  <div className="w-2 h-2 rounded-full shrink-0" style={{ background: clusterColor(node.cluster) }} />
                  <span className="text-xs text-slate-300 truncate">{node.label}</span>
                  <span className="text-[10px] text-slate-500 ml-auto shrink-0 tabular-nums">
                    {node.groups.length}g
                  </span>
                </div>
              ))}
            </div>
            <p className="text-[10px] text-slate-600 mt-4">Click a node or edge for details.</p>
          </div>
        )}
      </div>
    </div>
  )
}
