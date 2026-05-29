'use client'

import { useState } from 'react'
import { Calendar, Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { formatDate } from '@/lib/utils'
import { MessageModal } from './MessageModal'
import type { BoardReactivationTarget } from '@/types'

export function ReactivationCard({ target, onSkip }: { target: BoardReactivationTarget; onSkip: () => void }) {
  const [modalOpen, setModalOpen] = useState(false)
  const [showMessage, setShowMessage] = useState(false)
  const daysSince = Math.floor((Date.now() - new Date(target.lastContactDate).getTime()) / 86400000)

  return (
    <div className="bg-white border border-gray-200 border-l-4 border-l-purple-400 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-semibold text-gray-900">{target.contactName}</span>
            {target.company && <span className="text-gray-500 text-sm">· {target.company}</span>}
            <span className="text-xs bg-purple-50 text-purple-700 px-2 py-0.5 rounded-full flex items-center gap-1 ml-auto">
              <Calendar className="w-3 h-3" />{daysSince}d ago
            </span>
          </div>
          <p className="text-xs text-gray-500 mb-1">{target.email}</p>
          <p className="text-sm text-gray-600 mb-1 line-clamp-1">{target.history}</p>
          <p className="text-xs bg-purple-50 text-purple-700 rounded px-2 py-1">💡 {target.suggestedOffer}</p>
          {showMessage && (
            <p className="text-xs bg-gray-50 border rounded px-2 py-2 mt-2 italic text-gray-600 whitespace-pre-wrap">{target.suggestedMessage}</p>
          )}
        </div>
        <div className="flex flex-col gap-1.5 shrink-0">
          <Button size="sm" variant="outline" onClick={() => setShowMessage(!showMessage)} className="h-8 text-xs">
            {showMessage ? 'Hide' : 'Preview'}
          </Button>
          <Button size="sm" variant="outline" onClick={onSkip} className="h-8 text-xs">Skip</Button>
          <Button size="sm" onClick={() => setModalOpen(true)} className="h-8 text-xs bg-purple-600 hover:bg-purple-700 text-white">
            <Mail className="w-3 h-3 mr-1" />Reach Out
          </Button>
        </div>
      </div>
      <MessageModal open={modalOpen} onClose={() => setModalOpen(false)} to={target.email} context={`Reactivation: ${target.contactName} from ${target.company}. Last contact: ${formatDate(target.lastContactDate)}. History: ${target.history}. Offer: ${target.suggestedOffer}`} signalType="reactivation" />
    </div>
  )
}
