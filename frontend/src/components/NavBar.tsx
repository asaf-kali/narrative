import { NavLink, useMatch } from 'react-router-dom'

const BASE = 'flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors'
const ACTIVE = 'border-accent text-tx-primary'
const INACTIVE = 'border-transparent text-tx-muted hover:text-tx-primary'

export default function NavBar() {
  const inChat = useMatch('/chat/*')

  return (
    <nav className="bg-app-surface border-b border-app-border flex items-center px-2 flex-shrink-0">
      <NavLink to="/" end className={({ isActive }) => `${BASE} ${isActive ? ACTIVE : INACTIVE}`}>
        Summary
      </NavLink>

      {/* "Chats" is a section indicator — active on any /chat/* route, not a navigable destination */}
      <span className={`${BASE} cursor-default select-none ${inChat ? ACTIVE : INACTIVE}`}>
        Chats
      </span>

      <NavLink to="/messages" className={({ isActive }) => `${BASE} ${isActive ? ACTIVE : INACTIVE}`}>
        Messages
      </NavLink>

      <NavLink to="/network" className={({ isActive }) => `${BASE} ${isActive ? ACTIVE : INACTIVE}`}>
        Network
      </NavLink>
    </nav>
  )
}
