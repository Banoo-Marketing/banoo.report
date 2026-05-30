'use client'

import { useState } from 'react'
import { Mail, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { opportunityLabel, confidenceColor } from '@/lib/utils'
import { MessageModal } from './MessageModal'
import type { BoardOpportunity } from '@/types'

export function OpportunityCard({ op, onDismiss }: { op: BoardOpportunity; onDismiss: () => void }) {
  const [modalOpen, setModalOpen] = useState(false)
  const { label, emoji, cls } = opportunityLabel(op.opportunityScore)
  const confidence = op.revenueConfidence ?? op.opportunityScore

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-semibold text-gray-900 text-base">{op.contactName}</span>
            {op.company && <span className="text-gray-500 text-sm">· {op.company}</span>}
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${cls}`}>{emoji} {label}</span>
          </div>

          <p className="text-sm text-gray-700 mb-2">{op.reason}</p>

          <div className="flex items-center gap-4 mb-2">
            {op.estimatedValue && (
              <div>
                <span className="text-xs text-gray-500 uppercase tracking-wide">Potential Revenue</span>
                <p className="text-lg font-bold text-green-700">{op.estimatedValue}</p>
              </div>
            )}
            <div>
              <span className="text-xs text-gray-500 uppercase tracking-wide">Revenue Confidence</span>
              <p className={`text-lg font-bold ${confidenceColor(confidence)}`}>{confidence}%</p>
            </div>
          </div>

          <p className="text-xs font-medium text-blue-600">→ {op.suggestedAction}</p>
        </div>

        <div className="flex flex-col gap-2 shrink-0">
          <Button size="sm" onClick={() => setModalOpen(true)} className="h-8 text-xs bg-blue-600 hover:bg-blue-700">
            <Mail className="w-3 h-3 mr-1" />Draft Email
          </Button>
          <Button size="sm" variant="outline" onClick={onDismiss} className="h-8 text-xs">
            <CheckCircle className="w-3 h-3 mr-1" />Done
          </Button>
        </div>
      </div>

      <MessageModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        to={op.contactName}
        context={`Opportunity with ${op.contactName}${op.company ? ` at ${op.company}` : ''}. ${op.reason} Estimated value: ${op.estimatedValue ?? 'unknown'}. Suggested action: ${op.suggestedAction}.`}
        signalType="opportunity"
      />
    </div>
  )
}
