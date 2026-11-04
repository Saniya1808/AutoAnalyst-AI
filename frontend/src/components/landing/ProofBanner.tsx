import React from 'react'
import { ArrowRight } from 'lucide-react'

export const ProofBanner: React.FC = () => {
  return (
    <section className="proof-row section-wrap">
      <span>FROM RAW DATA TO REAL CLARITY</span>
      <div />
      <span>UPLOAD</span>
      <ArrowRight size={14} />
      <span>UNDERSTAND</span>
      <ArrowRight size={14} />
      <span>VISUALIZE</span>
      <ArrowRight size={14} />
      <span>DISCOVER</span>
    </section>
  )
}
