'use client'

import { useState } from 'react'
import { Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MessageModal } from './MessageModal'
import type { TopAction } from '@/types'

const CATEGORY = {
  opportunity: { label: 'MONEY', bg: 'bg-green-100 text-green-700', signal: 'opportunity' as const },
  churn: { label: 'SAVE CLIENT', bg: 'bg-red-100 text-red-700', signal: 'churn' as const },
  reactivation: { label: 'REACTIVATE', bg: 'bg-purple-100 text-purple-700', signal: 'reactivation' as const },
}

export function TodayCard({ action }: { action: TopAction }) {
  const [modalOpen, setModalOpen] = useState(false)
  const cfg = CATEGORY[action.type]

  const context = [
    `${action.name}${action.company ? ` at ${action.company}` : ''}.`,
    action.reason,
    action.estimatedValue ? `Estimated value: ${action.estimatedValue}.` : '',
    `Action: ${action.action}`,
  ].filter(Boolean).join(' ')

  return (
    <div className="border border-gray-200 rounded-xl p-5 hover:border-gray-300 transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Name + category */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full tracking-wide ${cfg.bg}`}>
              {cfg.label}
            </span>
            <span className="font-bold text-gray-900">{action.name}</span>
            {action.company && <span className="text-gray-500 text-sm">· {action.company}</span>}
            {action.estimatedValue && (
              <span className="text-green-700 text-xs font-semibold">{action.estimatedValue}</span>
            )}
          </div>

          {/* Reason */}
          <p className="text-sm text-gray-700 leading-snug mb-2">{action.reason}</p>

          {/* Action — imperative */}
          <p className="text-xs font-bold text-gray-900 uppercase tracking-wide">{action.action}</p>
        </div>

        <Button
          size="sm"
          onClick={() => setModalOpen(true)}
          className="shrink-0 h-9 bg-gray-900 hover:bg-gray-700 text-white text-sm font-semibold px-4"
        >
          <Mail className="w-3.5 h-3.5 mr-1.5" />
          Send Email
        </Button>
      </div>

      <MessageModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        to={action.email ?? action.name}
        context={context}
        signalType={cfg.signal}
      />
    </div>
  )
}
