'use client'

import { useState } from 'react'
import { Clock, Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MessageModal } from './MessageModal'
import type { BoardRetentionInsight } from '@/types'

export function RetentionCard({ insight, onDismiss }: { insight: BoardRetentionInsight; onDismiss: () => void }) {
  const [modalOpen, setModalOpen] = useState(false)

  return (
    <div className="bg-white border border-gray-200 border-l-4 border-l-blue-400 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-2">
            <span className="font-semibold text-gray-900">{insight.clientName}</span>
            <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full flex items-center gap-1">
              <Clock className="w-3 h-3" />{insight.timing}
            </span>
          </div>
          <p className="text-sm text-gray-600 mb-2">{insight.insight}</p>
          <p className="text-xs bg-blue-50 text-blue-800 rounded px-2 py-1 italic">💬 {insight.suggestedMessage}</p>
        </div>
        <div className="flex flex-col gap-1.5 shrink-0">
          <Button size="sm" variant="outline" onClick={onDismiss} className="h-8 text-xs">Skip</Button>
          <Button size="sm" onClick={() => setModalOpen(true)} className="h-8 text-xs bg-blue-600 hover:bg-blue-700">
            <Mail className="w-3 h-3 mr-1" />Draft
          </Button>
        </div>
      </div>
      <MessageModal open={modalOpen} onClose={() => setModalOpen(false)} to={insight.clientName} context={`Retention insight: ${insight.insight}. Timing: ${insight.timing}.`} signalType="retention" />
    </div>
  )
}
