'use client'

import { useState } from 'react'
import { ThumbsUp, ThumbsDown } from 'lucide-react'
import type { FeedbackValue, SignalKind } from '@/types'

interface Props {
  signalId: string
  signalType: SignalKind
  initialFeedback: FeedbackValue | null
}

async function postFeedback(signalId: string, signalType: SignalKind, feedback: FeedbackValue) {
  await fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ signalId, signalType, feedback }),
  })
}

export function FeedbackBar({ signalId, signalType, initialFeedback }: Props) {
  const [feedback, setFeedback] = useState<FeedbackValue | null>(initialFeedback)
  const [saving, setSaving] = useState(false)

  const handle = async (value: FeedbackValue) => {
    if (saving) return
    const next = feedback === value ? null : value
    setFeedback(next)
    setSaving(true)
    try {
      if (next) await postFeedback(signalId, signalType, next)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mt-3 pt-3 border-t border-gray-100 flex items-center gap-2">
      <span className="text-xs text-gray-400">Useful?</span>
      <button
        onClick={() => handle('useful')}
        disabled={saving}
        title="Good find"
        className={`flex items-center gap-1 text-xs px-2 py-1 rounded-full border transition-colors ${
          feedback === 'useful'
            ? 'bg-green-100 text-green-700 border-green-300'
            : 'text-gray-400 border-gray-200 hover:text-green-600 hover:border-green-300'
        }`}
      >
        <ThumbsUp className="w-3 h-3" />
        Yes
      </button>
      <button
        onClick={() => handle('not_useful')}
        disabled={saving}
        title="Not useful"
        className={`flex items-center gap-1 text-xs px-2 py-1 rounded-full border transition-colors ${
          feedback === 'not_useful'
            ? 'bg-red-100 text-red-700 border-red-300'
            : 'text-gray-400 border-gray-200 hover:text-red-600 hover:border-red-300'
        }`}
      >
        <ThumbsDown className="w-3 h-3" />
        No
      </button>
    </div>
  )
}
