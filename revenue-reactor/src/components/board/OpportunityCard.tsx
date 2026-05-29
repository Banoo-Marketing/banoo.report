'use client'

import { useState } from 'react'
import { Mail, CheckCircle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { opportunityLabel } from '@/lib/utils'
import { MessageModal } from './MessageModal'
import type { BoardOpportunity } from '@/types'

export function OpportunityCard({ op, onDismiss }: { op: BoardOpportunity; onDismiss: () => void }) {
  const [modalOpen, setModalOpen] = useState(false)
  const { label, emoji, cls } = opportunityLabel(op.opportunityScore)

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-semibold text-gray-900">{op.contactName}</span>
            {op.company && <span className="text-gray-500 text-sm">· {op.company}</span>}
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${cls}`}>{emoji} {label}</span>
          </div>
          <p className="text-sm text-gray-600 mb-2 line-clamp-2">{op.reason}</p>
          {op.evidence.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              {op.evidence.slice(0, 2).map((e, i) => (
                <span key={i} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{e}</span>
              ))}
            </div>
          )}
          <p className="text-xs text-blue-600 font-medium">→ {op.suggestedAction}</p>
        </div>
        <div className="flex flex-col items-end gap-2 shrink-0">
          {op.estimatedValue && <span className="text-lg font-bold text-green-700">{op.estimatedValue}</span>}
          <div className="flex gap-1.5">
            <Button size="sm" variant="outline" onClick={onDismiss} className="h-8 text-xs">
              <CheckCircle className="w-3 h-3 mr-1" />Done
            </Button>
            <Button size="sm" onClick={() => setModalOpen(true)} className="h-8 text-xs bg-blue-600 hover:bg-blue-700">
              <Mail className="w-3 h-3 mr-1" />Draft Email
            </Button>
          </div>
        </div>
      </div>
      <MessageModal open={modalOpen} onClose={() => setModalOpen(false)} to={op.contactName} context={`Opportunity: ${op.reason}. Suggested action: ${op.suggestedAction}. Estimated value: ${op.estimatedValue ?? 'unknown'}.`} signalType="opportunity" />
    </div>
  )
}
