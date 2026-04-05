import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { api } from '../api/client'

const COLORS = ['#0d9488', '#0891b2', '#7c3aed', '#db2777', '#f59e0b', '#84cc16', '#6366f1', '#94a3b8']

export default function ContentPage() {
  const { chatId } = useParams<{ chatId: string }>()
  const { data, isLoading } = useQuery({
    queryKey: ['words', chatId],
    queryFn: () => api.words(Number(chatId)),
    enabled: !!chatId,
  })
  const { data: emojiData = [], isLoading: eLoading } = useQuery({
    queryKey: ['emoji', chatId],
    queryFn: () => api.emoji(Number(chatId)),
    enabled: !!chatId,
  })

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
          <h3 className="text-sm font-semibold text-gray-600 mb-3">Word Cloud</h3>
          {isLoading ? (
            <div className="h-48 bg-gray-100 rounded animate-pulse" />
          ) : data?.wordcloud_png ? (
            <img src={data.wordcloud_png} alt="Word cloud" className="w-full rounded" />
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-400 text-sm">No text content</div>
          )}
        </div>
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
          <h3 className="text-sm font-semibold text-gray-600 mb-3">Top 20 Words</h3>
          {isLoading ? (
            <div className="h-48 bg-gray-100 rounded animate-pulse" />
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data?.frequencies.slice(0, 20)} layout="vertical">
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="word" tick={{ fontSize: 10 }} width={80} />
                <Tooltip />
                <Bar dataKey="count" name="Count">
                  {(data?.frequencies ?? []).slice(0, 20).map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
        <h3 className="text-sm font-semibold text-gray-600 mb-3">Emoji Usage</h3>
        {eLoading ? (
          <div className="h-48 bg-gray-100 rounded animate-pulse" />
        ) : (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={emojiData.slice(0, 20)} layout="vertical">
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="emoji" tick={{ fontSize: 16 }} width={40} />
              <Tooltip />
              <Bar dataKey="count" name="Count" fill="#0d9488" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
