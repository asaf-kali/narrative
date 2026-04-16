import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import ForceGraph2D, { type ForceGraphMethods, type NodeObject, type LinkObject } from 'react-force-graph-2d'
import { api } from '../api/client'
import type { NetworkNode } from '../api/types'
import { CardSpinner } from '../components/Spinner'

// Distinct palette for community clusters
const CLUSTER_COLORS = [
  '#7c5af6', '#0891b2', '#db2777', '#f59e0b',
  '#84cc16', '#6366f1', '#0d9488', '#f97316',
  '#a78bfa', '#22d3ee', '#fb7185', '#fbbf24',
]

type Mode = 'coactivity' | 'reactions'

interface GraphNode extends NodeObject {
  id: string
  label: string
  messages: number
  cluster: number
  centrality: number
}

interface GraphLink extends LinkObject {
  source: string | GraphNode
  target: string | GraphNode
  weight: number
}

function nodeColor(node: GraphNode): string {
  return CLUSTER_COLORS[node.cluster % CLUSTER_COLORS.length]
}

function StatRow({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-tx-muted">{label}</span>
      <span className="text-xs font-semibold text-tx-secondary tabular-nums">{value}</span>
    </div>
  )
}

function TopNode({ rank, node }: { rank: number; node: NetworkNode }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-tx-muted w-3 shrink-0">{rank}</span>
      <div className="w-2 h-2 rounded-full shrink-0" style={{ background: CLUSTER_COLORS[node.cluster % CLUSTER_COLORS.length] }} />
      <span className="text-xs text-tx-secondary truncate">{node.label}</span>
      <span className="text-[10px] text-tx-muted ml-auto shrink-0 tabular-nums">{(node.centrality * 100).toFixed(0)}%</span>
    </div>
  )
}

export default function NetworkPage() {
  const { chatId } = useParams<{ chatId: string }>()
  const { data: chats = [] } = useQuery({ queryKey: ['chats'], queryFn: () => api.chats() })
  const chat = chats.find((c) => c.chat_id === Number(chatId))

  const [mode, setMode] = useState<Mode>('coactivity')
  const [minWeight, setMinWeight] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['network', chatId, mode],
    queryFn: () => api.network(Number(chatId), mode),
    enabled: !!chatId,
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

  // Filtered graph data sent to the canvas
  const graphData = useMemo(() => {
    if (!data) return { nodes: [], links: [] }
    const visibleLinks = data.edges.filter((e) => e.weight >= minWeight)
    const visibleIds = new Set(visibleLinks.flatMap((e) => [e.source, e.target]))
    // Always show all nodes if no filter is applied
    const nodes = (minWeight <= 1 ? data.nodes : data.nodes.filter((n) => visibleIds.has(n.id))) as GraphNode[]
    const links: GraphLink[] = visibleLinks.map((e) => ({ source: e.source, target: e.target, weight: e.weight }))
    return { nodes, links }
  }, [data, minWeight])

  const maxWeight = useMemo(() => Math.max(1, ...( data?.edges.map((e) => e.weight) ?? [1])), [data])

  const topNodes = useMemo(
    () => [...(data?.nodes ?? [])].sort((a, b) => b.centrality - a.centrality).slice(0, 7),
    [data],
  )

  const handleNodeClick = useCallback((node: GraphNode) => {
    fgRef.current?.centerAt(node.x, node.y, 600)
    fgRef.current?.zoom(2.5, 600)
  }, [])

  if (chat && chat.chat_type !== 'group') {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center space-y-1">
          <p className="text-tx-secondary text-sm font-medium">Network analysis is only available for group chats</p>
          <p className="text-tx-muted text-xs">Direct and broadcast chats don't have enough participants to form a network.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-4 h-full min-h-0">
      {/* Graph panel */}
      <div className="flex-1 flex flex-col bg-app-surface border border-app-border rounded-xl overflow-hidden min-w-0">
        {/* Controls */}
        <div className="flex items-center gap-4 px-4 py-2.5 border-b border-app-border shrink-0">
          <div className="flex gap-1">
            {(['coactivity', 'reactions'] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setMinWeight(1) }}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  mode === m
                    ? 'bg-accent text-white shadow-lg shadow-accent/20'
                    : 'bg-app-surface-2 text-tx-secondary hover:text-tx-primary border border-app-border'
                }`}
              >
                {m === 'coactivity' ? 'Co-activity' : 'Reactions'}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 ml-auto">
            <span className="text-xs text-tx-muted">Min. interactions</span>
            <input
              type="range"
              min={1}
              max={maxWeight}
              value={minWeight}
              onChange={(e) => setMinWeight(Number(e.target.value))}
              className="w-28 accent-accent"
            />
            <span className="text-xs text-tx-secondary tabular-nums w-5 text-right">{minWeight}</span>
          </div>

          <button
            onClick={() => fgRef.current?.zoomToFit(400, 20)}
            className="text-[10px] text-tx-muted hover:text-tx-secondary transition-colors"
          >
            Fit
          </button>
        </div>

        {/* Canvas */}
        <div ref={containerRef} className="flex-1 min-h-0">
          {isLoading ? (
            <CardSpinner className="h-full" />
          ) : graphData.nodes.length === 0 ? (
            <div className="h-full flex items-center justify-center text-tx-muted text-sm">
              No data — try a different mode or lower the min. interactions slider.
            </div>
          ) : (
            <ForceGraph2D
              ref={fgRef}
              graphData={graphData}
              width={dims.width}
              height={dims.height}
              backgroundColor="#0d0f17"
              nodeLabel={(n) => `${(n as GraphNode).label} · ${(n as GraphNode).messages} msgs`}
              nodeColor={(n) => nodeColor(n as GraphNode)}
              nodeVal={(n) => Math.max(1, Math.sqrt((n as GraphNode).messages))}
              linkColor={() => 'rgba(255,255,255,0.08)'}
              linkWidth={(l) => Math.log1p((l as GraphLink).weight)}
              linkDirectionalArrowLength={mode === 'reactions' ? 5 : 0}
              linkDirectionalArrowRelPos={1}
              onNodeClick={(n) => handleNodeClick(n as GraphNode)}
              nodeCanvasObjectMode={() => 'after'}
              nodeCanvasObject={(node, ctx, globalScale) => {
                const n = node as GraphNode
                if (globalScale < 1.5) return
                const label = n.label.split(' ')[0]
                const fontSize = 10 / globalScale
                ctx.font = `${fontSize}px sans-serif`
                ctx.fillStyle = 'rgba(226,232,240,0.85)'
                ctx.textAlign = 'center'
                ctx.textBaseline = 'top'
                ctx.fillText(label, node.x ?? 0, (node.y ?? 0) + Math.sqrt(n.messages) + 2)
              }}
            />
          )}
        </div>
      </div>

      {/* Sidebar */}
      <div className="w-48 shrink-0 flex flex-col gap-3">
        <div className="bg-app-surface border border-app-border rounded-xl p-4 space-y-2">
          <h3 className="text-[9px] font-semibold text-tx-muted uppercase tracking-widest mb-3">Stats</h3>
          <StatRow label="Participants" value={data?.nodes.length ?? 0} />
          <StatRow label="Connections" value={graphData.links.length} />
          <StatRow label="Communities" value={data?.communities ?? 0} />
        </div>

        <div className="bg-app-surface border border-app-border rounded-xl p-4 flex-1">
          <h3 className="text-[9px] font-semibold text-tx-muted uppercase tracking-widest mb-3">Most Connected</h3>
          <div className="space-y-2.5">
            {topNodes.map((node, i) => (
              <TopNode key={node.id} rank={i + 1} node={node} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
