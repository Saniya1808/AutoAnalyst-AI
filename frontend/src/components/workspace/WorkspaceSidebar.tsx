import React from 'react'
import {
  Activity,
  BarChart3,
  CircleHelp,
  Files,
  Gauge,
  Home,
  Settings2,
} from 'lucide-react'

interface WorkspaceSidebarProps {
  onNavigateHome: () => void
  activeSection?: string
  onSelectSection?: (section: string) => void
}

export const WorkspaceSidebar: React.FC<WorkspaceSidebarProps> = ({
  onNavigateHome,
  activeSection = 'overview',
  onSelectSection,
}) => {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: Gauge },
    { id: 'datasets', label: 'My datasets', icon: Files },
    { id: 'dashboards', label: 'Dashboards', icon: BarChart3 },
    { id: 'analysis', label: 'AI analysis', icon: Activity },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-label">WORKSPACE</div>
      {navItems.map((item) => (
        <button
          key={item.id}
          type="button"
          className={`side-link ${activeSection === item.id ? 'active' : ''}`}
          onClick={() => onSelectSection?.(item.id)}
        >
          <item.icon size={17} /> {item.label}
        </button>
      ))}

      <div className="sidebar-bottom">
        <button
          type="button"
          className="side-link"
          onClick={onNavigateHome}
          title="Return to Landing Page"
        >
          <Home size={17} /> Landing page
        </button>
        <button
          type="button"
          className="side-link"
          onClick={() => alert('Settings configuration will be enabled in future phases.')}
        >
          <Settings2 size={17} /> Settings
        </button>
        <button
          type="button"
          className="side-link"
          onClick={() => alert('AutoAnalyst AI Documentation & Help center.')}
        >
          <CircleHelp size={17} /> Help center
        </button>
      </div>
    </aside>
  )
}
