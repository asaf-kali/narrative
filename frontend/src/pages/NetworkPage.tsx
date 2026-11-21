import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { NetworkSignal } from '../api/types'
import NetworkView from '../components/NetworkView'

const CHAT_SIGNALS: NetworkSignal[] = ['replies', 'reactions', 'mentions', 'adjacency']

export default function NetworkPage() {
  const { chatId } = useParams<{ chatId: string }>()
  const { data: chat } = useQuery({
    queryKey: ['chat', chatId],
    queryFn: () => api.chat(Number(chatId)),
    enabled: !!chatId,
  })

  const [signals, setSignals] = useState<NetworkSignal[]>(CHAT_SIGNALS)
  const isGroup = chat?.chat_type === 'group'

  const { data, isLoading } = useQuery({
    queryKey: ['network', chatId, [...signals].sort()],
    queryFn: () => api.network(Number(chatId), signals),
    enabled: !!chatId && isGroup,
  })

  if (chat && !isGroup) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center space-y-1">
          <p className="text-tx-secondary text-sm font-medium">Network analysis is only available for group chats</p>
          <p className="text-tx-muted text-xs">Direct and broadcast chats don't have enough participants to form a network.</p>
        </div>
      </div>
    )
  }

  return (
    <NetworkView
      data={data}
      isLoading={isLoading || !chat}
      availableSignals={CHAT_SIGNALS}
      signals={signals}
      onSignalsChange={setSignals}
    />
  )
}
