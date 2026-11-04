import React, { useState } from 'react'
import { ArrowRight, Menu, X } from 'lucide-react'
import { BrandLogo } from '../common/BrandLogo'
import { ThemeToggle } from '../common/ThemeToggle'
import { BackendStatusIndicator } from '../common/BackendStatusIndicator'
import type { ViewMode } from '../../types/navigation'

interface NavbarProps {
  onNavigate: (view: ViewMode) => void
}

export const Navbar: React.FC<NavbarProps> = ({ onNavigate }) => {
  const [menuOpen, setMenuOpen] = useState(false)

  const handleNavClick = (view: ViewMode) => {
    onNavigate(view)
    setMenuOpen(false)
  }

  return (
    <>
      <header className="topbar">
        <BrandLogo onClick={() => handleNavClick('home')} />

        <nav className="desktop-nav" aria-label="Main Navigation">
          <a href="#features">Features</a>
          <a href="#how-it-works">How it works</a>
          <a href="#about">About</a>
        </nav>

        <div className="top-actions">
          <BackendStatusIndicator compact />
          <ThemeToggle />
          <button
            type="button"
            className="button button-quiet desktop-only"
            onClick={() => handleNavClick('workspace')}
          >
            Workspace
          </button>
          <button
            type="button"
            className="button button-primary desktop-only"
            onClick={() => handleNavClick('workspace')}
          >
            Get started <ArrowRight size={16} />
          </button>
          <button
            type="button"
            className="icon-button mobile-menu"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle navigation menu"
          >
            {menuOpen ? <X size={19} /> : <Menu size={19} />}
          </button>
        </div>
      </header>

      {menuOpen && (
        <div className="mobile-nav" role="dialog" aria-modal="true">
          <a href="#features" onClick={() => setMenuOpen(false)}>
            Features
          </a>
          <a href="#how-it-works" onClick={() => setMenuOpen(false)}>
            How it works
          </a>
          <a href="#about" onClick={() => setMenuOpen(false)}>
            About
          </a>
          <div className="mobile-nav-divider" />
          <button
            type="button"
            className="button button-primary"
            onClick={() => handleNavClick('workspace')}
          >
            Launch workspace <ArrowRight size={15} />
          </button>
        </div>
      )}
    </>
  )
}
