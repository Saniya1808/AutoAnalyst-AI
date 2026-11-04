import React, { useRef } from 'react'
import { Bot, Sparkles, UploadCloud } from 'lucide-react'

export const WelcomeBanner: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      const names = Array.from(files).map((f) => f.name)
      alert(
        `Selected ${files.length} file(s):\n${names.join(
          ', '
        )}\n\n[Phase 1 Status]: Client file selection verified.\nSecure dataset upload, validation, and analytics pipeline will be activated in Phase 2.`
      )
      // Reset input safely
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  return (
    <div className="welcome-panel">
      <div>
        <div className="eyebrow">
          <Sparkles size={13} /> AUTONOMOUS DATA ANALYST
        </div>
        <h2>
          What would you like
          <br />
          to <span className="gradient-text">understand today?</span>
        </h2>
        <p>Upload a dataset and let AutoAnalyst AI help you explore it.</p>

        <button
          type="button"
          className="button button-primary"
          onClick={() => fileInputRef.current?.click()}
        >
          <UploadCloud size={17} /> Upload your data
        </button>

        <input
          ref={fileInputRef}
          id="file-upload"
          type="file"
          accept=".csv,.xlsx,.xls"
          multiple
          hidden
          onChange={handleFileChange}
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
