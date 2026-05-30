'use client'

import { useState } from 'react'
import { Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MessageModal } from './MessageModal'
import { FeedbackBar } from './FeedbackBar'
import type { BoardChurnSignal } from '@/types'

const RISK_STYLES = {
  high: { label: 'HIGH RISK', bar: 'border-l-red-500', badge: 'bg-red-100 text-red-700' },
  medium: { label: 'WATCH', bar: 'border-l-amber-500', badge: 'bg-amber-100 text-amber-700' },
  low: { label: 'LOW RISK', bar: 'border-l-gray-300', badge: 'bg-gray-100 text-gray-600' },
}

export function ChurnCard({ signal, index }: { signal: BoardChurnSignal; index: number }) {
  const [modalOpen, setModalOpen] = useState(false)
  const style = RISK_STYLES[signal.riskLevel as 'high' | 'medium' | 'low'] ?? RISK_STYLES.medium

  return (
    <div className={`bg-white border border-gray-200 border-l-4 ${style.bar} rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow`}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-gray-400">{index}.</span>
          <span className="font-bold text-gray-900 text-base">{signal.clientName}</span>
          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${style.badge}`}>{style.label}</span>
        </div>
        <Button
          size="sm"
          onClick={() => setModalOpen(true)}
          className="h-8 text-xs bg-red-600 hover:bg-red-700 text-white shrink-0"
        >
          <Mail className="w-3 h-3 mr-1" />
          Reach Out
        </Button>
      </div>

      {signal.whatHappened && (
        <div className="mb-2">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">What happened</p>
          <p className="text-sm text-gray-800 leading-relaxed">{signal.whatHappened}</p>
        </div>
      )}

      {signal.whyItMatters && (
        <div className="mb-3">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">Why it matters</p>
          <p className="text-sm text-gray-600 leading-relaxed">{signal.whyItMatters}</p>
        </div>
      )}

      <div className="bg-amber-50 rounded-lg px-3 py-2.5">
        <p className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-0.5">Recommended action</p>
        <p className="text-sm text-amber-900 font-medium">{signal.recommendedAction}</p>
      </div>

      <FeedbackBar signalId={signal.id} signalType="churn" initialFeedback={signal.userFeedback} />

      <MessageModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        to={signal.clientName}
        context={`${signal.clientName} is a client at risk of leaving. ${signal.whatHappened ?? signal.reasons.join('. ')} ${signal.whyItMatters ?? ''} Recommended action: ${signal.recommendedAction}`}
        signalType="churn"
      />
    </div>
  )
}
