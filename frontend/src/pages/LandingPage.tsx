import React from 'react'
import { motion } from 'framer-motion'
import { HeroSection } from '../components/landing/HeroSection'
import { ProofBanner } from '../components/landing/ProofBanner'
import { FeaturesSection } from '../components/landing/FeaturesSection'
import { WorkflowSection } from '../components/landing/WorkflowSection'
import { Footer } from '../components/layout/Footer'
import type { ViewMode } from '../types/navigation'

interface LandingPageProps {
  onNavigate: (view: ViewMode) => void
}

export const LandingPage: React.FC<LandingPageProps> = ({ onNavigate }) => {
  return (
    <motion.main
      key="home"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.35 }}
    >
      <HeroSection onStart={() => onNavigate('workspace')} />
      <ProofBanner />
      <FeaturesSection />
      <WorkflowSection />
      <Footer onNavigate={onNavigate} />
    </motion.main>
  )
}
