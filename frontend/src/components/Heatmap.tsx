import type { HeatmapPoint } from '../api/types'

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const HOURS = Array.from({ length: 24 }, (_, i) => i)

interface Props {
  data: HeatmapPoint[]
}

export default function Heatmap({ data }: Props) {
  const lookup = new Map(data.map((d) => [`${d.day}-${d.hour}`, d.count]))
  const maxVal = Math.max(...data.map((d) => d.count), 1)

  function cellColor(count: number): string {
    const intensity = count / maxVal
    const alpha = 0.06 + intensity * 0.94
    return `rgba(124, 90, 246, ${alpha.toFixed(2)})`
  }

  return (
    <div className="overflow-x-auto">
      <table className="text-xs border-collapse w-full">
        <thead>
          <tr>
            <th className="w-24" />
            {HOURS.map((h) => (
              <th key={h} className="text-center text-slate-500 font-normal pb-1 w-8">
                {h % 4 === 0 ? `${h}h` : ''}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {DAYS.map((day) => (
            <tr key={day}>
              <td className="text-slate-500 pr-2 text-right whitespace-nowrap">{day.slice(0, 3)}</td>
              {HOURS.map((hour) => {
                const count = lookup.get(`${day}-${hour}`) ?? 0
                return (
                  <td
                    key={hour}
                    title={`${day} ${hour}:00 — ${count} messages`}
                    className="w-8 h-6 rounded-sm"
                    style={{ backgroundColor: cellColor(count) }}
                  />
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
