import SearchableChipFilter from './SearchableChipFilter'

// ── component ─────────────────────────────────────────────────────────────────

interface Props {
  senders: string[]
  activeSenders: Set<string>
  onToggle: (sender: string) => void
  onClear: () => void
  isLoading?: boolean
}

/** Renders a searchable sender filter card. Returns null if ≤1 sender. */
export default function SenderFilterCard({ senders, activeSenders, onToggle, onClear, isLoading }: Props) {
  const items = senders.map((s) => ({ id: s, label: s, searchText: s }))
  return (
    <SearchableChipFilter
      title="Senders"
      items={items}
      activeIds={activeSenders}
      onToggle={onToggle}
      onClear={onClear}
      isLoading={isLoading}
    />
  )
}
