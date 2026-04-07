import type {
  Chat,
  ChatMessagesResponse,
  DayCount,
  DayDetail,
  EmojiItem,
  HeatmapPoint,
  MediaData,
  NetworkGraph,
  OverviewData,
  Participant,
  RangeDetail,
  SearchResult,
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
  chatMessages: (
    chatId: number,
    limit = 2000,
    offset = 0,
    dateFrom?: string,
    dateTo?: string,
    search?: string,
    senderId?: string,
  ): Promise<ChatMessagesResponse> => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
    if (dateFrom) params.set('date_from', dateFrom)
    if (dateTo) params.set('date_to', dateTo)
    if (search) params.set('search', search)
    if (senderId) params.set('sender_id', senderId)
    return get(`/api/chats/${chatId}/messages?${params}`)
  },
  search: (q: string, limit = 50): Promise<SearchResult[]> =>
    get(`/api/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  dayDetail: (date: string): Promise<DayDetail> => get(`/api/day/${date}`),
  rangeDetail: (from: string, to: string): Promise<RangeDetail> => {
    const params = new URLSearchParams({ date_from: from, date_to: to })
    return get(`/api/range?${params}`)
  },
  network: (chatId: number, mode: 'coactivity' | 'reactions' = 'coactivity'): Promise<NetworkGraph> =>
    get(`/api/chats/${chatId}/network?mode=${mode}`),
  globalNetwork: (mode: 'coactivity' | 'reactions' = 'coactivity', includeMe = true): Promise<NetworkGraph> =>
    get(`/api/network?mode=${mode}&include_me=${includeMe}`),
}
