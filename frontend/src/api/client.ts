import type {
  Chat,
  ChatIndexStatus,
  ChatMessagesResponse,
  DayCount,
  DayDetail,
  EmojiItem,
  GlobalMessagesResponse,
  HeatmapPoint,
  MediaData,
  MessageBounds,
  MessagesMetadata,
  NetworkGraph,
  OverviewData,
  Participant,
  RangeDetail,
  SearchResult,
  SemanticSearchHit,
  SenderInfo,
  TimelinePoint,
  WordData,
} from './types'

async function get<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export class SemanticUnavailableError extends Error {
  constructor() {
    super('Semantic search index not available')
  }
}

export const api = {
  chats: (search?: string): Promise<Chat[]> => {
    const params = new URLSearchParams()
    if (search) params.set('search', search)
    const qs = params.toString()
    return get(`/api/chats${qs ? `?${qs}` : ''}`)
  },
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
    sort?: 'asc' | 'desc',
  ): Promise<ChatMessagesResponse> => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
    if (dateFrom) params.set('date_from', dateFrom)
    if (dateTo) params.set('date_to', dateTo)
    if (search) params.set('search', search)
    if (senderId) params.set('sender_id', senderId)
    if (sort) params.set('sort', sort)
    return get(`/api/chats/${chatId}/messages?${params}`)
  },
  messageBounds: (chatId?: number): Promise<MessageBounds> => {
    const params = new URLSearchParams()
    if (chatId !== undefined) params.set('chat_id', String(chatId))
    const qs = params.toString()
    return get(`/api/messages/bounds${qs ? `?${qs}` : ''}`)
  },
  messagesMetadata: (
    dateFrom?: string,
    dateTo?: string,
    search?: string,
    chatIds?: number[],
    senderIds?: string[],
  ): Promise<MessagesMetadata> => {
    const params = new URLSearchParams()
    if (dateFrom) params.set('date_from', dateFrom)
    if (dateTo) params.set('date_to', dateTo)
    if (search) params.set('search', search)
    chatIds?.forEach((id) => params.append('chat_ids', String(id)))
    senderIds?.forEach((id) => params.append('sender_ids', id))
    return get(`/api/messages/metadata?${params}`)
  },
  globalMessages: (
    limit = 100,
    offset = 0,
    dateFrom?: string,
    dateTo?: string,
    search?: string,
    chatIds?: number[],
    senderIds?: string[],
    sort?: 'asc' | 'desc',
  ): Promise<GlobalMessagesResponse> => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
    if (dateFrom) params.set('date_from', dateFrom)
    if (dateTo) params.set('date_to', dateTo)
    if (search) params.set('search', search)
    chatIds?.forEach((id) => params.append('chat_ids', String(id)))
    senderIds?.forEach((id) => params.append('sender_ids', id))
    if (sort) params.set('sort', sort)
    return get(`/api/messages?${params}`)
  },
  senders: (senderIds?: string[]): Promise<SenderInfo[]> => {
    const params = new URLSearchParams()
    senderIds?.forEach((id) => params.append('sender_ids', id))
    const qs = params.toString()
    return get(`/api/senders${qs ? `?${qs}` : ''}`)
  },
  search: (q: string, limit = 50): Promise<SearchResult[]> =>
    get(`/api/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  semanticSearch: async (q: string, limit = 10, chatId?: number): Promise<SemanticSearchHit[]> => {
    const params = new URLSearchParams({ q, limit: String(limit) })
    if (chatId !== undefined) params.set('chat_id', String(chatId))
    const res = await fetch(`/api/semantic-search?${params}`)
    if (res.status === 503) throw new SemanticUnavailableError()
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
    return res.json() as Promise<SemanticSearchHit[]>
  },
  chatIndexStatus: (chatId: number): Promise<ChatIndexStatus> =>
    get<ChatIndexStatus>(`/api/chats/${chatId}/index-status`),

  indexChat: async (chatId: number): Promise<void> => {
    const res = await fetch(`/api/chats/${chatId}/index`, { method: 'POST' })
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  },

  dayDetail: (date: string): Promise<DayDetail> => get(`/api/day/${date}`),
  rangeDetail: (from: string, to: string): Promise<RangeDetail> => {
    const params = new URLSearchParams({ date_from: from, date_to: to })
    return get(`/api/range?${params}`)
  },
  network: (chatId: number, mode: 'coactivity' | 'reactions' = 'coactivity'): Promise<NetworkGraph> =>
    get(`/api/chats/${chatId}/network?mode=${mode}`),
  globalNetwork: (
    mode: 'coactivity' | 'reactions' = 'coactivity',
    includeMe = true,
    dateFrom?: string,
  ): Promise<NetworkGraph> => {
    const params = new URLSearchParams({ mode, include_me: String(includeMe) })
    if (dateFrom) params.set('date_from', dateFrom)
    return get(`/api/network?${params}`)
  },
}
