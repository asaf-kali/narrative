import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { useDebounce } from '../hooks/useDebounce'
import type { SearchResult } from '../api/types'

const MIN_LEN = 2

function formatTs(ts: string): string {
  // "YYYY-MM-DDTHH:MM:SS" → "YYYY-MM-DD HH:MM"
  return ts.slice(0, 10) + ' ' + ts.slice(11, 16)
}

function HighlightedSnippet({ text, term }: { text: string; term: string }) {
  const idx = text.toLowerCase().indexOf(term.toLowerCase())
  if (idx === -1) return <span className="text-slate-400 text-xs truncate">{text}</span>
  // Show ~40 chars around the match
  const start = Math.max(0, idx - 30)
  const end = Math.min(text.length, idx + term.length + 30)
  const snippet = (start > 0 ? '…' : '') + text.slice(start, end) + (end < text.length ? '…' : '')
  const snipIdx = snippet.indexOf(term.toLowerCase() === text.slice(idx, idx + term.length).toLowerCase() ? text.slice(idx, idx + term.length) : term)
  if (snipIdx === -1) return <span className="text-slate-400 text-xs">{snippet}</span>
  return (
    <span className="text-slate-400 text-xs">
      {snippet.slice(0, snipIdx)}
      <mark className="bg-accent/30 text-accent-light rounded-sm px-0.5 not-italic">
        {snippet.slice(snipIdx, snipIdx + term.length)}
      </mark>
      {snippet.slice(snipIdx + term.length)}
    </span>
  )
}

function ResultRow({ result, term, onSelect }: { result: SearchResult; term: string; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className="w-full flex items-start gap-3 px-4 py-2.5 hover:bg-white/[0.04] transition-colors text-left"
    >
      <div className="flex-1 min-w-0 space-y-0.5">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs font-medium text-slate-200 truncate">{result.chat_name}</span>
          <span className="text-[10px] text-slate-500 flex-shrink-0">·</span>
          <span className="text-[11px] text-slate-400 flex-shrink-0">{result.sender_name}</span>
        </div>
        <HighlightedSnippet text={result.text} term={term} />
      </div>
      <span className="text-[10px] text-slate-600 flex-shrink-0 mt-0.5">{formatTs(result.timestamp)}</span>
    </button>
  )
}

interface Props {
  open: boolean
  onClose: () => void
}

export default function GlobalSearch({ open, onClose }: Props) {
  const [input, setInput] = useState('')
  const query = useDebounce(input, 300)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  const { data: results = [], isFetching } = useQuery({
    queryKey: ['global-search', query],
    queryFn: () => api.search(query),
    enabled: query.length >= MIN_LEN,
    staleTime: 10_000,
  })

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setInput('')
      setTimeout(() => inputRef.current?.focus(), 30)
    }
  }, [open])

  // Close on Escape
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  function handleSelect(chatId: number) {
    navigate(`/chat/${chatId}/messages`)
    onClose()
  }

  const showResults = query.length >= MIN_LEN
  const noResults = showResults && !isFetching && results.length === 0

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed top-24 left-1/2 -translate-x-1/2 w-full max-w-xl z-50">
        <div className="bg-app-surface border border-app-border rounded-xl shadow-2xl overflow-hidden">
          {/* Input */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-app-border">
            <span className="text-slate-400 text-base flex-shrink-0">⌕</span>
            <input
              ref={inputRef}
              type="text"
              placeholder="Search all messages…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="flex-1 bg-transparent text-sm text-slate-200 placeholder-slate-600 focus:outline-none"
            />
            {isFetching && (
              <span className="text-[10px] text-slate-500 flex-shrink-0">searching…</span>
            )}
            <kbd className="text-[10px] text-slate-600 border border-app-border rounded px-1.5 py-0.5 flex-shrink-0">
              Esc
            </kbd>
          </div>

          {/* Results */}
          <div className="max-h-96 overflow-y-auto">
            {!showResults ? (
              <p className="px-4 py-6 text-center text-slate-600 text-xs">
                Type at least {MIN_LEN} characters to search
              </p>
            ) : noResults ? (
              <p className="px-4 py-6 text-center text-slate-500 text-sm">
                No results for "{query}"
              </p>
            ) : (
              <>
                <p className="px-4 pt-2 pb-1 text-[10px] text-slate-600">
                  {results.length} result{results.length !== 1 ? 's' : ''}
                  {results.length === 50 ? ' (showing first 50)' : ''}
                </p>
                <div className="divide-y divide-app-border/50">
                  {results.map((r, i) => (
                    <ResultRow
                      key={i}
                      result={r}
                      term={query}
                      onSelect={() => handleSelect(r.chat_id)}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
