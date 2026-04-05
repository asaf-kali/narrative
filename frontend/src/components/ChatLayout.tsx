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
    <div>
      <nav className="flex gap-1 mb-6 border-b border-gray-200 pb-0">
        {TABS.map((tab) => (
          <NavLink
            key={tab.path}
            to={tab.path === '' ? `/chat/${chatId}` : `/chat/${chatId}/${tab.path}`}
            end={tab.path === ''}
            className={({ isActive }) =>
              `px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition-colors ${
                isActive
                  ? 'border-teal-600 text-teal-700 bg-white'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-100'
              }`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  )
}
