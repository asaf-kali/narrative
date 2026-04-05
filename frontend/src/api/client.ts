import type {
  Chat,
  DayCount,
  EmojiItem,
  HeatmapPoint,
  MediaData,
  OverviewData,
  Participant,
  TimelinePoint,
  WordData,
} from './types'

async function get<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const api = {
  chats: (): Promise<Chat[]> => get('/api/chats'),
  dailyCounts: (): Promise<DayCount[]> => get('/api/stats/daily'),
  overview: (chatId: number): Promise<OverviewData> => get(`/api/chats/${chatId}/overview`),
  timeline: (chatId: number, period: 'daily' | 'monthly'): Promise<TimelinePoint[]> =>
    get(`/api/chats/${chatId}/timeline?period=${period}`),
  heatmap: (chatId: number): Promise<HeatmapPoint[]> => get(`/api/chats/${chatId}/heatmap`),
  participants: (chatId: number): Promise<Participant[]> => get(`/api/chats/${chatId}/participants`),
  words: (chatId: number): Promise<WordData> => get(`/api/chats/${chatId}/words`),
  emoji: (chatId: number): Promise<EmojiItem[]> => get(`/api/chats/${chatId}/emoji`),
  media: (chatId: number): Promise<MediaData> => get(`/api/chats/${chatId}/media`),
}
