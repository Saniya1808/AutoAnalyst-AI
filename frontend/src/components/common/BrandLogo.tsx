import React from 'react'
import { WandSparkles } from 'lucide-react'

interface BrandLogoProps {
  onClick?: () => void
  showBadge?: boolean
  size?: 'sm' | 'md'
}

export const BrandLogo: React.FC<BrandLogoProps> = ({
  onClick,
  showBadge = true,
  size = 'md',
}) => {
  return (
    <button
      type="button"
      className="brand"
      onClick={onClick}
      aria-label="AutoAnalyst AI home"
      style={{ cursor: onClick ? 'pointer' : 'default' }}
    >
      <span className={`brand-mark ${size === 'sm' ? 'brand-mark-sm' : ''}`}>
        <WandSparkles size={size === 'sm' ? 16 : 20} />
      </span>
      <div className="brand-text-group">
        <span className="brand-title">
          autoanalyst<span className="brand-ai">.ai</span>
        </span>
        {showBadge && (
          <span className="brand-author-tag">
            Powered by Saniya
          </span>
        )}
      </div>
    </button>
  )
}
