import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { WorkspaceSidebar } from '../components/workspace/WorkspaceSidebar'
import { WorkspaceTopBar } from '../components/workspace/WorkspaceTopBar'
import { WelcomeBanner } from '../components/workspace/WelcomeBanner'
import { MetricsSummary } from '../components/workspace/MetricsSummary'
import { RecentActivityPanel } from '../components/workspace/RecentActivityPanel'

interface WorkspacePageProps {
  onNavigateHome: () => void
}

export const WorkspacePage: React.FC<WorkspacePageProps> = ({ onNavigateHome }) => {
  const [activeSection, setActiveSection] = useState('overview')

  return (
    <motion.main
      key="workspace"
      className="workspace section-wrap"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.35 }}
    >
      <WorkspaceSidebar
        activeSection={activeSection}
        onSelectSection={setActiveSection}
        onNavigateHome={onNavigateHome}
      />
      <section className="workspace-main">
        <WorkspaceTopBar />
        <WelcomeBanner />
        <MetricsSummary />
        <RecentActivityPanel />
      </section>
    </motion.main>
  )
}
