export interface Chat {
  chat_id: number
  display_name: string
  chat_type: 'direct' | 'group' | 'broadcast'
  message_count: number
  date_first: string | null
  date_last: string | null
}

export interface OverviewData {
  total_messages: number
  active_days: number
  total_media: number
  total_audio: number
  total_links: number
  sparkline: Array<{ date: string; count: number }>
  type_breakdown: Array<{ label: string; count: number }>
}

export interface TimelinePoint {
  x: string
  sender_name: string
  count: number
}

export interface HeatmapPoint {
  day: string
  hour: number
  count: number
}

export interface Participant {
  sender_name: string
  messages: number
  pct: number
  words: number
  avg_words: number
  media: number
  audio: number
}

export interface WordData {
  frequencies: Array<{ word: string; count: number }>
  wordcloud_png: string
}

export interface EmojiItem {
  emoji: string
  count: number
}

export interface MediaData {
  breakdown: Array<{ type_label: string; count: number }>
  timeline: Array<{ month: string; type_label: string; count: number }>
}

export interface DayCount {
  date: string // "YYYY-MM-DD"
  count: number
}

export interface FeedMessage {
  timestamp: string   // "YYYY-MM-DDTHH:MM:SS"
  chat_name: string
  sender_name: string
  text: string | null
  message_type: number
}

export interface ChatMessagesResponse {
  total: number
  messages: FeedMessage[]
}

export interface DayMessage {
  time: string       // "HH:MM"
  chat_name: string
  sender_name: string
  text: string | null
  message_type: number
}

export interface DayBucket {
  bucket: string     // "HH:MM" 5-min resolution
  chat_name: string
  count: number
}

export interface DayDetail {
  date: string
  total_messages: number
  active_chats: number
  senders: string[]  // sorted by frequency desc
  timeline: DayBucket[]
  messages: DayMessage[]
}
