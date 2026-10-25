import type { ContactCard, FeedMessage, Location } from '../api/types'

// Type-specific details shown under a message (contact cards, locations, ...).

const CARD_CLASS = 'rounded-lg bg-app-hover px-2 py-1 min-w-0'

function mapUrl(loc: Location): string {
  return `https://www.openstreetmap.org/?mlat=${loc.latitude}&mlon=${loc.longitude}#map=16/${loc.latitude}/${loc.longitude}`
}

function coords(loc: Location): string {
  return `${loc.latitude.toFixed(5)}, ${loc.longitude.toFixed(5)}`
}

function ContactCards({ contacts }: { contacts: ContactCard[] }) {
  return (
    <>
      {contacts.map((c, i) => (
        <div key={i} className={CARD_CLASS}>
          <div className="text-[12px] font-medium text-tx-primary truncate">{c.name}</div>
          {c.phones.map((p) => (
            <div key={p} className="text-[11px] text-tx-muted tabular-nums truncate">{p}</div>
          ))}
        </div>
      ))}
    </>
  )
}

function LocationCard({ location }: { location: Location }) {
  return (
    <div className={CARD_CLASS}>
      {location.name && <div className="text-[12px] font-medium text-tx-primary truncate">{location.name}</div>}
      {location.address && <div className="text-[11px] text-tx-muted truncate">{location.address}</div>}
      <a
        href={mapUrl(location)}
        target="_blank"
        rel="noreferrer noopener"
        className="text-[11px] text-accent-light hover:underline tabular-nums"
      >
        {location.live ? 'Last seen at ' : ''}{coords(location)}
      </a>
    </div>
  )
}

/** Detail cards rendered inside a chat bubble; nothing when the message has none. */
export function AttachmentCards({ msg }: { msg: FeedMessage }) {
  const hasContacts = !!msg.contacts?.length
  if (!hasContacts && !msg.location) return null
  return (
    <div className="mt-1 flex flex-col gap-1">
      {hasContacts && <ContactCards contacts={msg.contacts!} />}
      {msg.location && <LocationCard location={msg.location} />}
    </div>
  )
}

/** Plain-text summary of a message's details, one line each — used as a hover tooltip. */
export function attachmentTooltip(msg: FeedMessage): string | undefined {
  const lines: string[] = []
  for (const c of msg.contacts ?? []) lines.push(c.phones.length ? `${c.name} (${c.phones.join(', ')})` : c.name)
  if (msg.location) {
    const label = [msg.location.name, msg.location.address].filter(Boolean).join(', ')
    lines.push(label ? `${label} (${coords(msg.location)})` : coords(msg.location))
  }
  return lines.length ? lines.join('\n') : undefined
}
