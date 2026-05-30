'use client'

import { useState } from 'react'
import { ThumbsUp, ThumbsDown, Phone, Trophy, XCircle, MinusCircle } from 'lucide-react'
import type { FeedbackValue, SignalKind } from '@/types'

interface Props {
  signalId: string
  signalType: SignalKind
  initialFeedback: FeedbackValue | null
  initialStatus: string
  showStatusButtons?: boolean
}

const STATUS_OPTIONS: { value: string; label: string; icon: React.ReactNode; cls: string }[] = [
  { value: 'contacted', label: 'Contacted', icon: <Phone className="w-3 h-3" />, cls: 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100' },
  { value: 'won', label: 'Won', icon: <Trophy className="w-3 h-3" />, cls: 'bg-green-50 text-green-700 border-green-200 hover:bg-green-100' },
  { value: 'lost', label: 'Lost', icon: <XCircle className="w-3 h-3" />, cls: 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100' },
  { value: 'not_interested', label: 'Not Interested', icon: <MinusCircle className="w-3 h-3" />, cls: 'bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100' },
]

async function postFeedback(signalId: string, signalType: SignalKind, feedback: FeedbackValue) {
  await fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ signalId, signalType, feedback }),
  })
}

async function patchStatus(signalId: string, signalType: SignalKind, status: string) {
  await fetch('/api/signal-status', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ signalId, signalType, status }),
  })
}

export function FeedbackBar({ signalId, signalType, initialFeedback, initialStatus, showStatusButtons = false }: Props) {
  const [feedback, setFeedback] = useState<FeedbackValue | null>(initialFeedback)
  const [status, setStatus] = useState(initialStatus)
  const [saving, setSaving] = useState(false)

  const handleFeedback = async (value: FeedbackValue) => {
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

  const handleStatus = async (value: string) => {
    if (saving) return
    const next = status === value ? (signalType === 'reactivation' ? 'pending' : 'new') : value
    setStatus(next)
    setSaving(true)
    try {
      await patchStatus(signalId, signalType, next)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between flex-wrap gap-2">
      {/* Feedback buttons */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-gray-400">Was this useful?</span>
        <button
          onClick={() => handleFeedback('useful')}
          disabled={saving}
          className={`flex items-center gap-1 text-xs px-2 py-1 rounded-full border transition-colors ${
            feedback === 'useful'
              ? 'bg-green-100 text-green-700 border-green-300'
              : 'bg-white text-gray-500 border-gray-200 hover:border-green-300 hover:text-green-600'
          }`}
        >
          <ThumbsUp className="w-3 h-3" />
          Good Find
        </button>
        <button
          onClick={() => handleFeedback('not_useful')}
          disabled={saving}
          className={`flex items-center gap-1 text-xs px-2 py-1 rounded-full border transition-colors ${
            feedback === 'not_useful'
              ? 'bg-red-100 text-red-700 border-red-300'
              : 'bg-white text-gray-500 border-gray-200 hover:border-red-300 hover:text-red-600'
          }`}
        >
          <ThumbsDown className="w-3 h-3" />
          Not Useful
        </button>
      </div>

      {/* Status buttons — only for opportunities */}
      {showStatusButtons && (
        <div className="flex items-center gap-1">
          {STATUS_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => handleStatus(opt.value)}
              disabled={saving}
              className={`flex items-center gap-1 text-xs px-2 py-1 rounded-full border transition-colors ${
                status === opt.value
                  ? opt.cls.replace('hover:', '') + ' font-semibold'
                  : 'bg-white text-gray-400 border-gray-200 hover:border-gray-300 hover:text-gray-600'
              }`}
            >
              {opt.icon}
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
