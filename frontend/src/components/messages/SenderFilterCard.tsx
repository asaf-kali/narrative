// ── component ─────────────────────────────────────────────────────────────────

interface Props {
  senders: string[]
  activeSenders: Set<string>
  onToggle: (sender: string) => void
  onClear: () => void
}

/** Renders a card with toggleable sender filter chips. Returns null if ≤1 sender. */
export default function SenderFilterCard({ senders, activeSenders, onToggle, onClear }: Props) {
  if (senders.length <= 1) return null
  return (
    <div className="bg-app-surface border border-app-border rounded-xl p-4">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[10px] text-slate-500 uppercase tracking-widest flex-shrink-0 mr-1">Senders</span>
        {senders.slice(0, 20).map((s) => (
          <button
            key={s}
            onClick={() => onToggle(s)}
            className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors border ${
              activeSenders.has(s)
                ? 'bg-accent/15 border-accent/50 text-accent-light'
                : 'bg-app-surface-2 border-app-border text-slate-400 hover:text-slate-200'
            }`}
          >
            {s}
          </button>
        ))}
        {activeSenders.size > 0 && (
          <button
            onClick={onClear}
            className="px-2.5 py-1 rounded-full text-[11px] text-slate-500 hover:text-slate-300 transition-colors"
          >
            Clear
          </button>
        )}
      </div>
    </div>
  )
}
