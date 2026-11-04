import React, { useRef, useState } from 'react'
import {
  AlertCircle,
  Bot,
  Loader2,
  ShieldAlert,
  Sparkles,
  UploadCloud,
  X,
} from 'lucide-react'

interface WelcomeBannerProps {
  isUploading?: boolean
  errorMessage?: string | null
  onClearError?: () => void
  onUploadFile: (file: File) => void
}

export const WelcomeBanner: React.FC<WelcomeBannerProps> = ({
  isUploading = false,
  errorMessage = null,
  onClearError,
  onUploadFile,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isDragOver, setIsDragOver] = useState(false)

  const handleFileSelected = (fileList: FileList | null) => {
    if (fileList && fileList.length > 0) {
      const file = fileList[0]
      onUploadFile(file)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    if (!isUploading && e.dataTransfer.files) {
      handleFileSelected(e.dataTransfer.files)
    }
  }

  return (
    <div
      className={`welcome-panel ${isDragOver ? 'drag-over' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div>
        <div className="eyebrow">
          <Sparkles size={13} /> AUTONOMOUS DATA ANALYST
        </div>
        <h2>
          What would you like
          <br />
          to <span className="gradient-text">understand today?</span>
        </h2>
        <p>
          Upload a CSV or Excel dataset to automatically generate profiling,
          schema distributions, and statistics.
        </p>

        {/* Public Demo Disclaimer Banner */}
        <div className="demo-disclaimer-banner" role="note">
          <ShieldAlert size={16} className="disclaimer-icon" />
          <span>
            <strong>Public Demo Environment:</strong> Uploaded datasets are anonymous and session-isolated. Do not upload confidential, sensitive, or proprietary data.
          </span>
        </div>

        {/* Error Alert if any */}
        {errorMessage && (
          <div className="upload-error-banner" role="alert">
            <div className="error-icon">
              <AlertCircle size={17} />
            </div>
            <div className="error-text">
              <strong>Upload Error:</strong> {errorMessage}
            </div>
            {onClearError && (
              <button
                type="button"
                className="error-dismiss-btn"
                onClick={onClearError}
                aria-label="Dismiss error"
              >
                <X size={14} />
              </button>
            )}
          </div>
        )}

        <div className="upload-action-row">
          <button
            type="button"
            className="button button-primary"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
          >
            {isUploading ? (
              <>
                <Loader2 size={17} className="spin-animation" />
                <span>Profiling dataset...</span>
              </>
            ) : (
              <>
                <UploadCloud size={17} />
                <span>Upload your data</span>
              </>
            )}
          </button>

          <span className="upload-specs-badge">
            CSV, XLSX, XLS • Max 25 MB • Up to 100k rows
          </span>
        </div>

        <input
          ref={fileInputRef}
          id="file-upload"
          type="file"
          accept=".csv,.xlsx,.xls"
          hidden
          onChange={(e) => handleFileSelected(e.target.files)}
        />
      </div>

      <div className="welcome-art">
        <div className="art-ring ring-one" />
        <div className="art-ring ring-two" />
        <div className="art-core">
          <Bot size={43} />
        </div>
        <span className="art-spark spark-one">✦</span>
        <span className="art-spark spark-two">✧</span>
      </div>
    </div>
  )
}
