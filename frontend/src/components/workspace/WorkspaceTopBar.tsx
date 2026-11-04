import React from 'react'
import { Bell } from 'lucide-react'
import { BackendStatusIndicator } from '../common/BackendStatusIndicator'

export const WorkspaceTopBar: React.FC = () => {
  return (
    <div className="workspace-top">
      <div>
        <div className="eyebrow">YOUR WORKSPACE</div>
        <h2>Welcome back, analyst.</h2>
        <p>Your next insight starts with a dataset.</p>
      </div>

      <div className="workspace-actions">
        <BackendStatusIndicator />
        <button
          type="button"
          className="icon-button"
          aria-label="Notifications"
          onClick={() => alert('No new notifications.')}
        >
          <Bell size={17} />
        </button>
        <div className="avatar" title="Saniya - System Lead">
          S
        </div>
      </div>
    </div>
  )
}
