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
  const { data: chats = [], isLoading } = useQuery({
    queryKey: ['chats'],
    queryFn: api.chats,
  })

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar chats={chats} isLoading={isLoading} />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Header />
        <main className="flex-1 overflow-auto p-6 bg-gray-50">
          <Routes>
            <Route path="/" element={<HomePage />} />
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
