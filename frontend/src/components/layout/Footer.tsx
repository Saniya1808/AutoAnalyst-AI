import React from 'react'
import { BrandLogo } from '../common/BrandLogo'
import type { ViewMode } from '../../types/navigation'

interface FooterProps {
  onNavigate?: (view: ViewMode) => void
}

export const Footer: React.FC<FooterProps> = ({ onNavigate }) => {
  return (
    <footer className="footer section-wrap" id="about">
      <div className="footer-left">
        <BrandLogo size="sm" onClick={() => onNavigate?.('home')} />
        <span className="footer-tagline">
          Designed with intelligence. Built for discovery.
        </span>
      </div>

      <div className="footer-right">
        <div className="footer-links">
          <a href="#features">Features</a>
          <a href="#how-it-works">Architecture</a>
          <button
            type="button"
            className="footer-link-btn"
            onClick={() => onNavigate?.('workspace')}
          >
            Workspace
          </button>
        </div>
        <span className="copyright-tag">
          © 2026 AutoAnalyst AI · Powered by Saniya
        </span>
      </div>
    </footer>
  )
}
