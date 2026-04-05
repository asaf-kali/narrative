export default function Header() {
  return (
    <header className="bg-app-surface border-b border-app-border px-6 py-3 flex items-center justify-between flex-shrink-0">
      <h1 className="text-sm font-semibold text-slate-200 tracking-tight">WhatsApp Analyzer</h1>
      <span className="text-[11px] text-app-muted">All processing is local — no data leaves your device</span>
    </header>
  )
}
