import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { NetworkSignal } from '../api/types'
import NetworkView, { ContactsOnlyToggle } from '../components/NetworkView'
import { boolParam, intParam, listParam, useUrlState } from '../hooks/useUrlState'

const CHAT_SIGNALS: NetworkSignal[] = ['replies', 'reactions', 'mentions', 'adjacency']

// clusters 0 = let the backend pick
const URL_DEFAULTS = { signals: CHAT_SIGNALS, contacts: true, backbone: false, clusters: 0 }
const URL_CODECS = { signals: listParam(CHAT_SIGNALS), contacts: boolParam, backbone: boolParam, clusters: intParam }

export default function NetworkPage() {
  const { chatId } = useParams<{ chatId: string }>()
  const { data: chat } = useQuery({
    queryKey: ['chat', chatId],
    queryFn: () => api.chat(Number(chatId)),
    enabled: !!chatId,
  })

  const [{ signals, contacts: contactsOnly, backbone, clusters }, setUrlState] = useUrlState(URL_DEFAULTS, URL_CODECS)
  const isGroup = chat?.chat_type === 'group'

  const { data, isLoading } = useQuery({
    queryKey: ['network', chatId, [...signals].sort(), contactsOnly, clusters],
    queryFn: () => api.network(Number(chatId), signals, contactsOnly, clusters),
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
      onSignalsChange={(next) => setUrlState({ signals: next })}
      backboneOnly={backbone}
      onBackboneOnlyChange={(next) => setUrlState({ backbone: next })}
      clusters={clusters}
      onClustersChange={(next) => setUrlState({ clusters: next })}
      controls={<ContactsOnlyToggle checked={contactsOnly} onChange={(next) => setUrlState({ contacts: next })} />}
    />
  )
}
