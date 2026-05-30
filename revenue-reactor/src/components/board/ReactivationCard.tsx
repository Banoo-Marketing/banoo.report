'use client'

import { useState } from 'react'
import { Calendar, Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MessageModal } from './MessageModal'
import { FeedbackBar } from './FeedbackBar'
import type { BoardReactivationTarget } from '@/types'

export function ReactivationCard({ target, onSkip }: { target: BoardReactivationTarget; onSkip: () => void }) {
  const [modalOpen, setModalOpen] = useState(false)
  const daysSince = Math.floor((Date.now() - new Date(target.lastContactDate).getTime()) / 86400000)
  const monthsAgo = Math.floor(daysSince / 30)

  return (
    <div className="bg-white border border-gray-200 border-l-4 border-l-purple-400 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-semibold text-gray-900 text-base">{target.contactName}</span>
            {target.company && <span className="text-gray-500 text-sm">· {target.company}</span>}
            <span className="text-xs bg-purple-50 text-purple-700 px-2 py-0.5 rounded-full flex items-center gap-1 ml-auto">
              <Calendar className="w-3 h-3" />
              {monthsAgo > 0 ? `${monthsAgo} month${monthsAgo !== 1 ? 's' : ''} ago` : `${daysSince}d ago`}
            </span>
          </div>

          {target.whyContact && (
            <div className="mb-2">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-0.5">Why Contact Now</p>
              <p className="text-sm text-gray-700">{target.whyContact}</p>
            </div>
          )}

          {!target.whyContact && (
            <p className="text-sm text-gray-600 mb-2">{target.history}</p>
          )}

          <div className="bg-purple-50 border border-purple-100 rounded-lg px-3 py-2">
            <p className="text-xs font-semibold text-purple-700 mb-0.5">Suggested Offer</p>
            <p className="text-sm text-purple-800">{target.suggestedOffer}</p>
          </div>
        </div>

        <div className="flex flex-col gap-1.5 shrink-0">
          <Button size="sm" onClick={() => setModalOpen(true)} className="h-8 text-xs bg-purple-600 hover:bg-purple-700 text-white">
            <Mail className="w-3 h-3 mr-1" />Reach Out
          </Button>
          <Button size="sm" variant="outline" onClick={onSkip} className="h-8 text-xs">Skip</Button>
        </div>
      </div>

      <FeedbackBar
        signalId={target.id}
        signalType="reactivation"
        initialFeedback={target.userFeedback}
        initialStatus={target.status}
      />

      <MessageModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        to={target.email}
        context={`Reactivation outreach to ${target.contactName}${target.company ? ` at ${target.company}` : ''}. Last contact: ${monthsAgo} months ago. ${target.whyContact ?? target.history} Suggested offer: ${target.suggestedOffer}`}
        signalType="reactivation"
      />
    </div>
  )
}
