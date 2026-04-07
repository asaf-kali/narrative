// ── helpers ───────────────────────────────────────────────────────────────────

function shortName(name: string, max = 20): string {
  return name.length > max ? name.slice(0, max - 1) + '…' : name
}

// ── component ─────────────────────────────────────────────────────────────────

interface Props {
  chatNames: string[]
  activeChats: Set<string>
  colorMap: Map<string, string>
  onToggle: (chat: string) => void
  onClear: () => void
}

/** Renders a card with toggleable chat filter chips. Returns null if ≤1 chat. */
export default function ChatsFilterCard({ chatNames, activeChats, colorMap, onToggle, onClear }: Props) {
  if (chatNames.length <= 1) return null
  return (
    <div className="bg-app-surface border border-app-border rounded-xl p-4">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[10px] text-slate-500 uppercase tracking-widest flex-shrink-0 mr-1">Chats</span>
        {chatNames.map((chat) => (
          <button
            key={chat}
            onClick={() => onToggle(chat)}
            className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors border truncate max-w-[160px] ${
              activeChats.has(chat)
                ? 'border-accent/50 text-accent-light'
                : 'bg-app-surface-2 border-app-border text-slate-400 hover:text-slate-200'
            }`}
            style={activeChats.has(chat) ? { backgroundColor: (colorMap.get(chat) ?? '#7c5af6') + '22' } : undefined}
            title={chat}
          >
            {shortName(chat)}
          </button>
        ))}
        {activeChats.size > 0 && (
          <button
            onClick={onClear}
            className="px-2 py-1 text-[11px] text-slate-500 hover:text-slate-300 transition-colors"
          >
            Clear
          </button>
        )}
      </div>
    </div>
  )
}
