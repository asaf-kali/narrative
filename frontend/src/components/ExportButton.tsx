import { useState } from 'react'
import type { FeedMessage } from '../api/types'

const PAGE_SIZE = 1000

type Format = 'csv' | 'json'

interface Props {
  onFetchPage: (limit: number, offset: number) => Promise<{ messages: FeedMessage[] }>
  total: number
  filename: string
  disabled?: boolean
}

function toUTC(ts: string): string {
  return new Date(ts).toISOString()
}

function toCSV(messages: FeedMessage[]): string {
  const header = ['timestamp_utc', 'chat_name', 'sender_name', 'text', 'message_type']
  const escape = (v: string | number | null | undefined) => {
    const s = v == null ? '' : String(v)
    if (s.includes(',') || s.includes('"') || s.includes('\n')) {
      return `"${s.replace(/"/g, '""')}"`
    }
    return s
  }
  const rows = messages.map((m) =>
    [toUTC(m.timestamp), m.chat_name, m.sender_name, m.text, m.message_type].map(escape).join(','),
  )
  return [header.join(','), ...rows].join('\n')
}

function triggerDownload(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export default function ExportButton({ onFetchPage, total, filename, disabled }: Props) {
  const [showPicker, setShowPicker] = useState(false)
  const [progress, setProgress] = useState<string | null>(null)

  async function runExport(format: Format) {
    setShowPicker(false)
    const totalPages = Math.ceil(total / PAGE_SIZE)
    const all: FeedMessage[] = []

    for (let page = 0; page < totalPages; page++) {
      setProgress(`Fetching ${page + 1} / ${totalPages}…`)
      const res = await onFetchPage(PAGE_SIZE, page * PAGE_SIZE)
      all.push(...res.messages)
    }

    setProgress('Building file…')

    if (format === 'csv') {
      triggerDownload(toCSV(all), `${filename}.csv`, 'text/csv')
    } else {
      const withUTC = all.map((m) => ({ ...m, timestamp: toUTC(m.timestamp) }))
      triggerDownload(JSON.stringify(withUTC, null, 2), `${filename}.json`, 'application/json')
    }

    setProgress(null)
  }

  const isExporting = progress !== null
  const label = isExporting ? progress : `↓ Export (${total.toLocaleString()})`

  return (
    <div className="relative flex-shrink-0">
      <button
        onClick={() => !isExporting && setShowPicker((v) => !v)}
        disabled={disabled || isExporting}
        className="px-2 py-1 rounded text-[11px] font-medium transition-colors border bg-app-surface-2 border-app-border text-tx-muted hover:text-tx-primary disabled:opacity-40"
      >
        {label}
      </button>

      {showPicker && !isExporting && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setShowPicker(false)} />
          <div className="absolute right-0 top-full mt-1 z-20 bg-app-surface border border-app-border rounded-lg shadow-lg overflow-hidden flex flex-col min-w-[80px]">
            {(['csv', 'json'] as Format[]).map((fmt) => (
              <button
                key={fmt}
                onClick={() => runExport(fmt)}
                className="px-4 py-2 text-xs text-tx-secondary hover:bg-app-surface-2 hover:text-tx-primary transition-colors text-left uppercase font-mono"
              >
                {fmt}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
