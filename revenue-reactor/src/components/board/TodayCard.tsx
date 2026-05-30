'use client'

import { useState } from 'react'
import { Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MessageModal } from './MessageModal'
import type { TopAction } from '@/types'

const TYPE_CONFIG = {
  opportunity: { label: 'OPPORTUNITY', bg: 'bg-blue-100 text-blue-700', signal: 'opportunity' as const },
  churn: { label: 'AT RISK', bg: 'bg-red-100 text-red-700', signal: 'churn' as const },
  reactivation: { label: 'REACTIVATE', bg: 'bg-purple-100 text-purple-700', signal: 'reactivation' as const },
}

export function TodayCard({ action, rank }: { action: TopAction; rank: number }) {
  const [modalOpen, setModalOpen] = useState(false)
  const cfg = TYPE_CONFIG[action.type]

  const context = [
    `${action.name}${action.company ? ` at ${action.company}` : ''}.`,
    action.reason,
    action.estimatedValue ? `Estimated value: ${action.estimatedValue}.` : '',
    `Suggested action: ${action.action}`,
  ].filter(Boolean).join(' ')

  return (
    <div className="flex items-start gap-4 py-4 border-b border-gray-100 last:border-0">
      <span className="text-sm font-bold text-gray-300 w-5 shrink-0 mt-0.5">{rank}.</span>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${cfg.bg}`}>
            {cfg.label}
          </span>
          <span className="font-bold text-gray-900 text-sm">{action.name}</span>
          {action.company && <span className="text-gray-500 text-sm">· {action.company}</span>}
          {action.estimatedValue && (
            <span className="text-green-700 text-xs font-semibold">{action.estimatedValue}</span>
          )}
        </div>
        <p className="text-sm text-gray-700 leading-snug line-clamp-2">{action.reason}</p>
        <p className="text-xs font-semibold text-gray-900 mt-1">{action.action}</p>
      </div>

      <Button
        size="sm"
        onClick={() => setModalOpen(true)}
        className="h-8 text-xs shrink-0 bg-gray-900 hover:bg-gray-700 text-white"
      >
        <Mail className="w-3 h-3 mr-1" />
        Email
      </Button>

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
