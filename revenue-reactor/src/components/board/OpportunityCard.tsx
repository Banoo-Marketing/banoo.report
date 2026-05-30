'use client'

import { useState } from 'react'
import { Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MessageModal } from './MessageModal'
import { FeedbackBar } from './FeedbackBar'
import type { BoardOpportunity } from '@/types'

export function OpportunityCard({ op, index }: { op: BoardOpportunity; index: number }) {
  const [modalOpen, setModalOpen] = useState(false)

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs font-bold text-gray-400">{index}.</span>
            <span className="font-bold text-gray-900 text-base">{op.contactName}</span>
            {op.company && <span className="text-gray-500 text-sm">· {op.company}</span>}
          </div>
          {op.estimatedValue && (
            <span className="text-green-700 font-bold text-sm">{op.estimatedValue}</span>
          )}
        </div>
        <Button
          size="sm"
          onClick={() => setModalOpen(true)}
          className="h-8 text-xs bg-blue-600 hover:bg-blue-700 shrink-0"
        >
          <Mail className="w-3 h-3 mr-1" />
          Send Email
        </Button>
      </div>

      <div className="space-y-2 mb-3">
        <div>
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">What happened</p>
          <p className="text-sm text-gray-800 leading-relaxed">{op.reason}</p>
        </div>

        {op.evidence.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">Evidence</p>
            <ul className="space-y-0.5">
              {op.evidence.map((e, i) => (
                <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                  <span className="text-gray-400 mt-0.5 shrink-0">·</span>
                  {e}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="bg-blue-50 rounded-lg px-3 py-2.5 mb-1">
        <p className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-0.5">What to do</p>
        <p className="text-sm text-blue-900 font-medium">{op.suggestedAction}</p>
      </div>

      <FeedbackBar
        signalId={op.id}
        signalType="opportunity"
        initialStatus={op.status}
        initialFeedback={op.userFeedback}
        initialRevenue={op.revenueRecovered}
      />

      <MessageModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        to={op.contactName}
        context={`${op.contactName}${op.company ? ` at ${op.company}` : ''}. ${op.reason} Evidence: ${op.evidence.join(', ')}. Value: ${op.estimatedValue ?? 'unknown'}. Action needed: ${op.suggestedAction}.`}
        signalType="opportunity"
      />
    </div>
  )
}
