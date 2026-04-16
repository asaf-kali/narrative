import { useRef } from 'react'

export const DATETIME_RE = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/

/** Format a Date as "YYYY-MM-DD HH:MM" in local time. */
export function formatDatetime(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    d.getFullYear() + '-' +
    pad(d.getMonth() + 1) + '-' +
    pad(d.getDate()) + ' ' +
    pad(d.getHours()) + ':' +
    pad(d.getMinutes())
  )
}

/** Convert "YYYY-MM-DD HH:MM" to ISO "YYYY-MM-DDTHH:MM" for the API. */
export function toApiDatetime(s: string): string {
  return s.replace(' ', 'T')
}

interface DatetimeInputProps {
  value: string
  onChange: (v: string) => void
  isInvalid?: boolean
  placeholder?: string
}

export default function DatetimeInput({ value, onChange, isInvalid = false, placeholder = 'yyyy-mm-dd HH:MM' }: DatetimeInputProps) {
  const pickerRef = useRef<HTMLInputElement>(null)

  const pickerValue = DATETIME_RE.test(value) ? value.replace(' ', 'T') : ''

  function handlePickerChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (!e.target.value) return
    onChange(formatDatetime(new Date(e.target.value)))
  }

  const borderClass = isInvalid
    ? 'border-red-500/70 focus:border-red-500 focus:ring-red-500/20'
    : 'border-app-border focus:border-accent/50 focus:ring-accent/20'

  return (
    <div className="relative">
      <input
        type="text"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        onClick={() => pickerRef.current?.showPicker()}
        className={`bg-app-surface-2 border rounded px-2 py-1.5 text-tx-secondary placeholder-tx-muted focus:outline-none focus:ring-1 w-40 cursor-pointer ${borderClass}`}
      />
      <input
        ref={pickerRef}
        type="datetime-local"
        value={pickerValue}
        onChange={handlePickerChange}
        className="sr-only"
        tabIndex={-1}
        aria-hidden
      />
    </div>
  )
}
