import { useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { ThemeProvider } from './context/ThemeContext'
import { Navbar } from './components/layout/Navbar'
import { LandingPage } from './pages/LandingPage'
import { WorkspacePage } from './pages/WorkspacePage'
import type { ViewMode } from './types/navigation'

function AppContent() {
  const [view, setView] = useState<ViewMode>('home')

  return (
    <div className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <Navbar onNavigate={setView} />

      <AnimatePresence mode="wait">
        {view === 'home' ? (
          <LandingPage key="home" onNavigate={setView} />
        ) : (
          <WorkspacePage key="workspace" onNavigateHome={() => setView('home')} />
        )}
      </AnimatePresence>
    </div>
  )
}

function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  )
}

export default App
