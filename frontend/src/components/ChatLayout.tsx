import { NavLink, Outlet, useParams } from 'react-router-dom'

const TABS = [
  { label: 'Overview', path: '' },
  { label: 'Timeline', path: 'timeline' },
  { label: 'Participants', path: 'participants' },
  { label: 'Words & Emoji', path: 'content' },
  { label: 'Media', path: 'media' },
]

export default function ChatLayout() {
  const { chatId } = useParams<{ chatId: string }>()

  return (
    <div className="flex flex-col h-full">
      <nav className="flex gap-0.5 px-5 pt-4 border-b border-app-border flex-shrink-0">
        {TABS.map((tab) => (
          <NavLink
            key={tab.path}
            to={tab.path === '' ? `/chat/${chatId}` : `/chat/${chatId}/${tab.path}`}
            end={tab.path === ''}
            className={({ isActive }) =>
              `px-3.5 py-2 text-xs font-medium rounded-t-md border-b-2 -mb-px transition-colors ${
                isActive
                  ? 'border-accent text-slate-100 bg-app-surface-2'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
              }`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
      <div className="flex-1 overflow-auto p-5">
        <Outlet />
      </div>
    </div>
  )
}
