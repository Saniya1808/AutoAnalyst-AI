import React from 'react'
import { ArrowRight, FileSpreadsheet } from 'lucide-react'

export const RecentActivityPanel: React.FC = () => {
  const triggerUpload = () => {
    document.getElementById('file-upload')?.click()
  }

  return (
    <div className="recent-panel">
      <div>
        <h3>Recent activity</h3>
        <p>Your latest datasets, automated profiling, and visual charts will show up here.</p>
      </div>

      <div className="empty-state">
        <div>
          <FileSpreadsheet size={23} />
        </div>
        <b>Your workspace is ready</b>
        <span>Upload your first CSV or Excel file to get started.</span>
        <button
          type="button"
          className="text-button"
          onClick={triggerUpload}
        >
          Choose a file <ArrowRight size={14} />
        </button>
      </div>
    </div>
  )
}
