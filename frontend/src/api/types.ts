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
