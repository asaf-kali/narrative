import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { api } from '../api/client'

const COLORS = ['#0d9488', '#0891b2', '#7c3aed', '#db2777', '#f59e0b', '#84cc16', '#6366f1', '#94a3b8']

export default function ParticipantsPage() {
  const { chatId } = useParams<{ chatId: string }>()
  const { data = [], isLoading } = useQuery({
    queryKey: ['participants', chatId],
    queryFn: () => api.participants(Number(chatId)),
    enabled: !!chatId,
  })

  if (isLoading) return <div className="h-64 bg-gray-200 rounded-xl animate-pulse" />

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
        <h3 className="text-sm font-semibold text-gray-600 mb-4">Message Distribution</h3>
        <ResponsiveContainer width="100%" height={Math.max(200, data.length * 36)}>
          <BarChart data={data} layout="vertical">
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="sender_name" tick={{ fontSize: 11 }} width={120} />
            <Tooltip formatter={(v: number) => v.toLocaleString()} />
            <Bar dataKey="messages" name="Messages">
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 overflow-x-auto">
        <h3 className="text-sm font-semibold text-gray-600 mb-3">Detailed Stats</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left border-b border-gray-100">
              {['Name', 'Messages', '%', 'Words', 'Avg words', 'Media', 'Audio'].map((h) => (
                <th key={h} className="py-2 pr-4 text-gray-500 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((p, i) => (
              <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="py-2 pr-4 font-medium text-gray-800">{p.sender_name}</td>
                <td className="py-2 pr-4">{p.messages.toLocaleString()}</td>
                <td className="py-2 pr-4">{p.pct}%</td>
                <td className="py-2 pr-4">{Number(p.words).toLocaleString()}</td>
                <td className="py-2 pr-4">{p.avg_words}</td>
                <td className="py-2 pr-4">{p.media}</td>
                <td className="py-2 pr-4">{p.audio}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
