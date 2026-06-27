// Human-readable date formatting, used everywhere a date is displayed
// (NOT the date-picker inputs, which keep the yyyy-mm-dd HH:MM machine format).

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const DATE_ONLY_RE = /^(\d{4})-(\d{2})-(\d{2})$/
const NAIVE_DATETIME_RE = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?$/

function pad2(n: number): string {
  return String(n).padStart(2, '0')
}

// Parse into a local-time Date. Date-only and timezone-less datetime strings are
// treated as local (no UTC shift); ISO strings with an offset/Z are honoured.
function toLocalDate(input: string | number | Date): Date {
  if (input instanceof Date) return input
  if (typeof input === 'number') return new Date(input)

  const s = input.trim()
  const dateOnly = DATE_ONLY_RE.exec(s)
  if (dateOnly) {
    const [, y, m, d] = dateOnly
    return new Date(Number(y), Number(m) - 1, Number(d))
  }
  const naive = NAIVE_DATETIME_RE.exec(s)
  if (naive) {
    const [, y, m, d, h, min, sec] = naive
    return new Date(Number(y), Number(m) - 1, Number(d), Number(h), Number(min), Number(sec ?? 0))
  }
  return new Date(s)
}

// "07 Jun, 2025"
export function formatDate(input: string | number | Date | null | undefined): string {
  if (input == null || input === '' || input === '—') return '—'
  const d = toLocalDate(input)
  if (Number.isNaN(d.getTime())) return typeof input === 'string' ? input : '—'
  return `${pad2(d.getDate())} ${MONTHS[d.getMonth()]}, ${d.getFullYear()}`
}

// "07 Jun, 2025, 14:30"
export function formatDateTime(input: string | number | Date | null | undefined): string {
  if (input == null || input === '' || input === '—') return '—'
  const d = toLocalDate(input)
  if (Number.isNaN(d.getTime())) return typeof input === 'string' ? input : '—'
  return `${formatDate(d)}, ${pad2(d.getHours())}:${pad2(d.getMinutes())}`
}
