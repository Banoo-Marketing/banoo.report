'use client'

import { useState } from 'react'
import { Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MessageModal } from './MessageModal'
import { FeedbackBar } from './FeedbackBar'
import type { BoardReactivationTarget } from '@/types'

export function ReactivationCard({ target, index }: { target: BoardReactivationTarget; index: number }) {
  const [modalOpen, setModalOpen] = useState(false)
  const daysSince = Math.floor((Date.now() - new Date(target.lastContactDate).getTime()) / 86400000)
  const monthsAgo = Math.floor(daysSince / 30)
  const timeLabel = monthsAgo >= 2 ? `${monthsAgo} months ago` : monthsAgo === 1 ? '1 month ago' : `${daysSince} days ago`

  return (
    <div className="bg-white border border-gray-200 border-l-4 border-l-purple-400 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs font-bold text-gray-400">{index}.</span>
            <span className="font-bold text-gray-900 text-base">{target.contactName}</span>
            {target.company && <span className="text-gray-500 text-sm">· {target.company}</span>}
          </div>
          <span className="text-xs text-purple-600 font-medium">Last contact: {timeLabel}</span>
        </div>
        <Button
          size="sm"
          onClick={() => setModalOpen(true)}
          className="h-8 text-xs bg-purple-600 hover:bg-purple-700 text-white shrink-0"
        >
          <Mail className="w-3 h-3 mr-1" />
          Reach Out
        </Button>
      </div>

      {target.whyContact && (
        <div className="mb-3">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">Why contact now</p>
          <p className="text-sm text-gray-800 leading-relaxed">{target.whyContact}</p>
        </div>
      )}

      {/* Suggested message shown inline */}
      <div className="bg-purple-50 rounded-lg px-3 py-3">
        <p className="text-xs font-semibold text-purple-600 uppercase tracking-wide mb-1.5">Suggested message</p>
        <p className="text-sm text-purple-900 leading-relaxed whitespace-pre-line">{target.suggestedMessage}</p>
      </div>

      <FeedbackBar signalId={target.id} signalType="reactivation" initialFeedback={target.userFeedback} />

      <MessageModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        to={target.email}
        context={`Reactivation outreach to ${target.contactName}${target.company ? ` at ${target.company}` : ''}. Last contact was ${timeLabel}. ${target.whyContact ?? target.history} Suggested offer: ${target.suggestedOffer}`}
        signalType="reactivation"
      />
    </div>
  )
}
