import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import ChatLayout from './components/ChatLayout'
import NavBar from './components/NavBar'
import { CardSpinner } from './components/Spinner'
import { ThemeProvider } from './context/ThemeContext'

const HomePage = lazy(() => import('./pages/HomePage'))
const OverviewPage = lazy(() => import('./pages/OverviewPage'))
const TimelinePage = lazy(() => import('./pages/TimelinePage'))
const ParticipantsPage = lazy(() => import('./pages/ParticipantsPage'))
const ContentPage = lazy(() => import('./pages/ContentPage'))
const MediaPage = lazy(() => import('./pages/MediaPage'))
const MessagesPage = lazy(() => import('./pages/MessagesPage'))
const NetworkPage = lazy(() => import('./pages/NetworkPage'))
const GlobalNetworkPage = lazy(() => import('./pages/GlobalNetworkPage'))
const GlobalMessagesPage = lazy(() => import('./pages/GlobalMessagesPage'))

export default function App() {
  return (
    <ThemeProvider>
      <div className="flex h-screen overflow-hidden bg-app-bg text-tx-primary">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          <Header />
          <NavBar />
          <main className="flex-1 overflow-hidden">
            <Suspense fallback={<div className="flex h-full items-center justify-center"><CardSpinner /></div>}>
              <Routes>
                <Route path="/" element={<div className="h-full overflow-auto p-6"><HomePage /></div>} />
                <Route path="/messages" element={<div className="h-full overflow-auto p-6"><GlobalMessagesPage /></div>} />
                <Route path="/network" element={<div className="h-full overflow-hidden p-4"><GlobalNetworkPage /></div>} />
                <Route path="/chat/:chatId" element={<ChatLayout />}>
                  <Route index element={<OverviewPage />} />
                  <Route path="timeline" element={<TimelinePage />} />
                  <Route path="participants" element={<ParticipantsPage />} />
                  <Route path="content" element={<ContentPage />} />
                  <Route path="media" element={<MediaPage />} />
                  <Route path="messages" element={<MessagesPage />} />
                  <Route path="network" element={<NetworkPage />} />
                </Route>
              </Routes>
            </Suspense>
          </main>
        </div>
      </div>
    </ThemeProvider>
  )
}
