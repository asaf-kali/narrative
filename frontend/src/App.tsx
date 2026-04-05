import { Route, Routes } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from './api/client'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import HomePage from './pages/HomePage'
import OverviewPage from './pages/OverviewPage'
import TimelinePage from './pages/TimelinePage'
import ParticipantsPage from './pages/ParticipantsPage'
import ContentPage from './pages/ContentPage'
import MediaPage from './pages/MediaPage'
import ChatLayout from './components/ChatLayout'

export default function App() {
  const { data: chats = [], isLoading } = useQuery({ queryKey: ['chats'], queryFn: api.chats })

  return (
    <div className="flex h-screen overflow-hidden bg-app-bg text-slate-200">
      <Sidebar chats={chats} isLoading={isLoading} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<div className="h-full overflow-auto p-6"><HomePage /></div>} />
            <Route path="/chat/:chatId" element={<ChatLayout />}>
              <Route index element={<OverviewPage />} />
              <Route path="timeline" element={<TimelinePage />} />
              <Route path="participants" element={<ParticipantsPage />} />
              <Route path="content" element={<ContentPage />} />
              <Route path="media" element={<MediaPage />} />
            </Route>
          </Routes>
        </main>
      </div>
    </div>
  )
}
