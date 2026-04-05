import type { DayCount } from '../api/types'

interface Props {
  data: DayCount[]
  selectedDate: string | null
  onSelectDate: (date: string) => void
}

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

interface Cell {
  date: string // YYYY-MM-DD or '' for padding
  count: number
}

/** Returns Monday of the ISO week containing `d`. */
function toMonday(d: Date): Date {
  const result = new Date(d)
  // getDay(): 0=Sun, 1=Mon … 6=Sat → shift so Mon=0
  const dow = (d.getDay() + 6) % 7
  result.setDate(d.getDate() - dow)
  result.setHours(0, 0, 0, 0)
  return result
}

function addDays(d: Date, n: number): Date {
  const result = new Date(d)
  result.setDate(d.getDate() + n)
  return result
}

function toISO(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function buildGrid(data: DayCount[]): { weeks: Cell[][]; monthLabels: { label: string; colIndex: number }[] } {
  if (data.length === 0) return { weeks: [], monthLabels: [] }

  const countMap = new Map(data.map((d) => [d.date, d.count]))
  const firstDate = new Date(data[0].date + 'T00:00:00')
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const start = toMonday(firstDate)
  const end = toMonday(today)

  const weeks: Cell[][] = []
  const monthLabels: { label: string; colIndex: number }[] = []
  let seenMonth = -1

  let weekStart = new Date(start)
  while (weekStart <= end) {
    const week: Cell[] = []
    for (let i = 0; i < 7; i++) {
      const d = addDays(weekStart, i)
      if (d > today) {
        week.push({ date: '', count: 0 })
      } else {
        const iso = toISO(d)
        week.push({ date: iso, count: countMap.get(iso) ?? 0 })
      }
    }
    // Track month labels (label on first week of a new month)
    const repDate = addDays(weekStart, 3) // mid-week representative
    if (repDate.getMonth() !== seenMonth) {
      seenMonth = repDate.getMonth()
      monthLabels.push({ label: MONTHS[seenMonth], colIndex: weeks.length })
    }
    weeks.push(week)
    weekStart = addDays(weekStart, 7)
  }

  return { weeks, monthLabels }
}

function cellColor(count: number, max: number, isSelected: boolean): string {
  if (isSelected) return '#0369a1' // highlight blue
  if (count === 0) return '#f1f5f9'
  const t = Math.sqrt(count / max) // sqrt scale so low values are visible
  const r = Math.round(240 - t * 225)
  const g = Math.round(253 - t * 97)
  const b = Math.round(244 - t * 100)
  return `rgb(${r},${g},${b})`
}

export default function CalendarHeatmap({ data, selectedDate, onSelectDate }: Props) {
  const { weeks, monthLabels } = buildGrid(data)
  const max = Math.max(...data.map((d) => d.count), 1)

  if (weeks.length === 0) {
    return <div className="text-gray-400 text-sm text-center py-8">No data</div>
  }

  return (
    <div className="overflow-x-auto">
      {/* Month labels */}
      <div className="flex mb-1" style={{ paddingLeft: '2.5rem' }}>
        {weeks.map((_, wi) => {
          const label = monthLabels.find((m) => m.colIndex === wi)
          return (
            <div key={wi} className="text-xs text-gray-400 flex-shrink-0" style={{ width: '14px', marginRight: '2px' }}>
              {label ? label.label : ''}
            </div>
          )
        })}
      </div>

      {/* Grid: rows = days of week, columns = weeks */}
      <div className="flex gap-0">
        {/* Day labels */}
        <div className="flex flex-col mr-1 flex-shrink-0">
          {DAYS.map((d, i) => (
            <div
              key={d}
              className="text-xs text-gray-400 flex items-center justify-end pr-1"
              style={{ height: '14px', marginBottom: '2px', width: '2rem', visibility: i % 2 === 0 ? 'visible' : 'hidden' }}
            >
              {d}
            </div>
          ))}
        </div>

        {/* Week columns */}
        {weeks.map((week, wi) => (
          <div key={wi} className="flex flex-col flex-shrink-0" style={{ marginRight: '2px' }}>
            {week.map((cell, di) => (
              <div
                key={di}
                title={cell.date ? `${cell.date}: ${cell.count.toLocaleString()} messages` : ''}
                onClick={() => cell.date && cell.count > 0 && onSelectDate(cell.date)}
                className={`rounded-sm flex-shrink-0 ${cell.date && cell.count > 0 ? 'cursor-pointer hover:ring-2 hover:ring-teal-400 hover:ring-offset-1' : ''}`}
                style={{
                  width: '14px',
                  height: '14px',
                  marginBottom: '2px',
                  backgroundColor: cell.date ? cellColor(cell.count, max, cell.date === selectedDate) : 'transparent',
                }}
              />
            ))}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-1 mt-3 justify-end text-xs text-gray-400">
        <span>Less</span>
        {[0, 0.2, 0.4, 0.7, 1].map((t) => (
          <div
            key={t}
            className="w-3 h-3 rounded-sm"
            style={{ backgroundColor: t === 0 ? '#f1f5f9' : cellColor(Math.ceil(t * max), max, false) }}
          />
        ))}
        <span>More</span>
      </div>
    </div>
  )
}
