import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { api } from '../api/client'

const COLORS = ['#7c5af6', '#0891b2', '#0d9488', '#db2777', '#f59e0b', '#84cc16', '#6366f1', '#94a3b8']
const TOOLTIP_STYLE = { background: '#0d0f17', border: '1px solid #1a1d2e', color: '#e2e8f0', borderRadius: 8, fontSize: 12 }
const TICK_STYLE = { fill: '#64748b', fontSize: 10 }

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
        <div className="bg-app-surface border border-app-border rounded-xl p-4">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-4">Word Cloud</h3>
          {isLoading ? (
            <div className="h-48 bg-app-surface-2 rounded animate-pulse" />
          ) : data?.wordcloud_png ? (
            <img src={data.wordcloud_png} alt="Word cloud" className="w-full rounded" />
          ) : (
            <div className="h-48 flex items-center justify-center text-slate-500 text-sm">No text content</div>
          )}
        </div>
        <div className="bg-app-surface border border-app-border rounded-xl p-4">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-4">Top 20 Words</h3>
          {isLoading ? (
            <div className="h-48 bg-app-surface-2 rounded animate-pulse" />
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data?.frequencies.slice(0, 20)} layout="vertical">
                <XAxis type="number" tick={TICK_STYLE} />
                <YAxis type="category" dataKey="word" tick={TICK_STYLE} width={80} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
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

      <div className="bg-app-surface border border-app-border rounded-xl p-4">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-4">Emoji Usage</h3>
        {eLoading ? (
          <div className="h-48 bg-app-surface-2 rounded animate-pulse" />
        ) : (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={emojiData.slice(0, 20)} layout="vertical">
              <XAxis type="number" tick={TICK_STYLE} />
              <YAxis type="category" dataKey="emoji" tick={{ fontSize: 16, fill: '#94a3b8' }} width={40} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Bar dataKey="count" name="Count" fill="#7c5af6" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
