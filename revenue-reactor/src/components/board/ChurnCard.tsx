'use client'

import { useState } from 'react'
import { AlertTriangle, Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { churnLabel } from '@/lib/utils'
import { MessageModal } from './MessageModal'
import type { BoardChurnSignal } from '@/types'

export function ChurnCard({ signal, onResolve }: { signal: BoardChurnSignal; onResolve: () => void }) {
  const [modalOpen, setModalOpen] = useState(false)
  const { label, emoji, cls, border } = churnLabel(signal.churnScore, signal.riskLevel)

  return (
    <div className={`bg-white border border-gray-200 border-l-4 ${border} rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-2">
            <span className="font-semibold text-gray-900">{signal.clientName}</span>
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${cls}`}>{emoji} {label}</span>
            <span className="text-xs text-gray-500 ml-auto">Score: {signal.churnScore}/100</span>
          </div>
          {signal.reasons.map((r, i) => (
            <div key={i} className="flex items-start gap-1.5 text-sm text-gray-600 mb-0.5">
              <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
              {r}
            </div>
          ))}
          <p className="text-xs text-gray-500 italic mt-2 bg-gray-50 rounded px-2 py-1">{signal.recommendedAction}</p>
        </div>
        <div className="flex flex-col gap-1.5 shrink-0">
          <Button size="sm" variant="outline" onClick={onResolve} className="h-8 text-xs">Resolved</Button>
          <Button size="sm" onClick={() => setModalOpen(true)} className="h-8 text-xs bg-red-600 hover:bg-red-700 text-white">
            <Mail className="w-3 h-3 mr-1" />Reach Out
          </Button>
        </div>
      </div>
      <MessageModal open={modalOpen} onClose={() => setModalOpen(false)} to={signal.clientName} context={`Client churn risk. Reasons: ${signal.reasons.join(', ')}. Recommended action: ${signal.recommendedAction}`} signalType="churn" />
    </div>
  )
}
