export interface Chat {
  chat_id: number
  display_name: string
  chat_type: 'direct' | 'group' | 'broadcast'
  message_count: number
  date_first: string | null
  date_last: string | null
  phone: string | null
  is_lid: boolean
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
  sender_id: string    // "me" | phone number — stable across renames
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

export interface SearchResult {
  chat_id: number
  chat_name: string
  sender_name: string
  timestamp: string   // "YYYY-MM-DDTHH:MM:SS"
  text: string
}

export interface DayCount {
  date: string // "YYYY-MM-DD"
  count: number
}

export interface EmojiCount {
  emoji: string
  count: number
}

export interface MessageReactions {
  emojis: EmojiCount[]
  total: number
  reactors: string[]   // display names of everyone who reacted
}

export interface ReplyPreview {
  quoted_message_id: number | null   // resolved original message id (null if deleted)
  sender_name: string
  text: string | null
  message_type: number
}

export interface ContactCard {
  name: string
  phones: string[]
}

export interface Location {
  latitude: number
  longitude: number
  name: string | null
  address: string | null
  live: boolean        // live share: coordinates are the last known position
}

export interface PollOption {
  name: string
  votes: number
}

export interface Poll {
  options: PollOption[]
  multiple_choice: boolean
}

export interface CallInfo {
  video: boolean
  duration_seconds: number
  outcome: 'completed' | 'missed' | 'busy' | 'declined' | 'unknown'
}

export interface FeedMessage {
  message_id?: number
  timestamp: string    // "YYYY-MM-DDTHH:MM:SS"
  chat_id: number
  chat_name: string
  sender_id: string    // "me" | phone number
  sender_name: string
  text: string | null
  message_type: number
  reactions?: MessageReactions | null
  reply_to?: ReplyPreview | null
  contacts?: ContactCard[] | null   // shared vCards (message_type 4 / 14)
  location?: Location | null        // pin or live location (message_type 5 / 16)
  poll?: Poll | null                // options + vote totals; question is `text` (message_type 66)
  call?: CallInfo | null            // in-chat call event (message_type 90)
}

export interface ReactionStat {
  sender_name: string
  reactions_received: number
  reactions_given: number
}

export interface ReplyStat {
  sender_name: string
  replies_received: number
  replies_sent: number
}

export interface TopReactedMessage {
  message_id: number
  sender_name: string
  text: string | null
  message_type: number
  emojis: string   // "😂 5 ❤️ 2"
  total: number
  timestamp: string   // "YYYY-MM-DDTHH:MM:SS" local time
}

export interface EngagementData {
  emoji_breakdown: EmojiCount[]
  reaction_leaderboard: ReactionStat[]
  top_reacted: TopReactedMessage[]
  reply_leaderboard: ReplyStat[]
}

export interface ChatMessagesResponse {
  total: number
  messages: FeedMessage[]
}

export interface GlobalMessagesResponse {
  messages: FeedMessage[]
}

export interface MessagesMetadata {
  total: number
  available_chat_ids: number[]
  available_sender_ids: string[]
}

export interface MessageBounds {
  first_ts: number | null
  last_ts: number | null
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

export interface RangeMessage {
  timestamp: string   // "YYYY-MM-DDTHH:MM" local time
  chat_name: string
  sender_name: string
  text: string | null
  message_type: number
}

export interface RangeBucket {
  bucket: string      // "YYYY-MM-DD"
  chat_name: string
  count: number
}

export interface NetworkNode {
  id: string
  label: string
  messages: number
  cluster: number
  centrality: number
  groups: string[]
}

export interface NetworkEdge {
  source: string
  target: string
  weight: number
}

export interface NetworkGraph {
  nodes: NetworkNode[]
  edges: NetworkEdge[]
  communities: number
  mode: string
}

export interface SenderInfo {
  sender_id: string   // "me" | phone digits | name fallback
  sender_name: string
  phone: string
  message_count: number
}

export interface SemanticSearchHit {
  chat_id: number
  chat_name: string
  timestamp_start: string  // ISO 8601 datetime
  timestamp_end: string    // ISO 8601 datetime
  text: string             // "Sender: message" lines for this session — snippet/preview
  score: number
}

export interface RangeDetail {
  date_from: string
  date_to: string
  total_messages: number
  active_chats: number
  senders: string[]
  buckets: string[]     // all 30 bucket start labels ("YYYY-MM-DDTHH:MM")
  timeline: RangeBucket[]
  messages: RangeMessage[]
}

export interface ChatIndexStatus {
  status: 'indexed' | 'partial' | 'none'
  session_count: number
}
