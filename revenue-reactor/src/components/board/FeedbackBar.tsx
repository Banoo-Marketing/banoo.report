'use client'

import { useState } from 'react'
import { Check, X, DollarSign } from 'lucide-react'
import type { FeedbackValue, SignalKind } from '@/types'

interface Props {
  signalId: string
  signalType: SignalKind
  initialStatus: string
  initialFeedback: FeedbackValue | null
  initialRevenue?: number | null
}

async function patchStatus(signalId: string, signalType: SignalKind, status: string) {
  await fetch('/api/signal-status', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ signalId, signalType, status }),
  })
}

async function postIgnored(signalId: string, signalType: SignalKind) {
  await fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ signalId, signalType, feedback: 'not_useful' }),
  })
}

async function markWon(opportunityId: string, amount: number) {
  await fetch('/api/revenue-won', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ opportunityId, amount }),
  })
}

export function FeedbackBar({ signalId, signalType, initialStatus, initialFeedback, initialRevenue }: Props) {
  const isWon = initialStatus === 'won'
  const isContacted = initialStatus === 'contacted' || isWon
  const isIgnored = initialFeedback === 'not_useful'

  const [contacted, setContacted] = useState(isContacted)
  const [ignored, setIgnored] = useState(isIgnored)
  const [won, setWon] = useState(isWon)
  const [revenue, setRevenue] = useState<number | null>(initialRevenue ?? null)
  const [showWonInput, setShowWonInput] = useState(false)
  const [wonInput, setWonInput] = useState('')
  const [saving, setSaving] = useState(false)

  const handleContacted = async () => {
    if (saving || contacted) return
    setSaving(true)
    await patchStatus(signalId, signalType, 'contacted')
    setContacted(true)
    setSaving(false)
  }

  const handleIgnored = async () => {
    if (saving || ignored) return
    setSaving(true)
    await postIgnored(signalId, signalType)
    setIgnored(true)
    setSaving(false)
  }

  const handleWon = async () => {
    const amount = parseFloat(wonInput.replace(/[$,]/g, ''))
    if (isNaN(amount) || amount < 0) return
    setSaving(true)
    await markWon(signalId, amount)
    setRevenue(amount)
    setWon(true)
    setShowWonInput(false)
    setSaving(false)
  }

  if (ignored) {
    return (
      <div className="mt-3 pt-3 border-t border-gray-100">
        <span className="text-xs text-gray-400 italic">Marked as not useful — won&apos;t show again</span>
      </div>
    )
  }

  return (
    <div className="mt-3 pt-3 border-t border-gray-100">
      <div className="flex items-center gap-2 flex-wrap">
        {contacted ? (
          <span className="flex items-center gap-1 text-xs text-green-700 bg-green-50 border border-green-200 px-2.5 py-1 rounded-full font-medium">
            <Check className="w-3 h-3" /> Contacted
          </span>
        ) : (
          <button
            onClick={handleContacted}
            disabled={saving}
            className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-full border border-gray-300 text-gray-600 hover:border-green-400 hover:text-green-700 hover:bg-green-50 transition-colors"
          >
            <Check className="w-3 h-3" /> Contacted
          </button>
        )}

        {!won && !ignored && (
          <button
            onClick={handleIgnored}
            disabled={saving}
            className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-full border border-gray-300 text-gray-500 hover:border-red-300 hover:text-red-600 hover:bg-red-50 transition-colors"
          >
            <X className="w-3 h-3" /> Ignore
          </button>
        )}

        {signalType === 'opportunity' && contacted && !won && (
          <>
            {showWonInput ? (
              <div className="flex items-center gap-1.5 flex-wrap">
                <div className="flex items-center border border-green-300 rounded-full overflow-hidden">
                  <span className="pl-2.5 text-xs text-green-700">$</span>
                  <input
                    type="text"
                    placeholder="0"
                    value={wonInput}
                    onChange={e => setWonInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleWon()}
                    className="w-20 text-xs px-1.5 py-1 outline-none bg-transparent text-green-800"
                    autoFocus
                  />
                </div>
                <button
                  onClick={handleWon}
                  disabled={saving}
                  className="text-xs px-2.5 py-1 rounded-full bg-green-600 text-white font-medium hover:bg-green-700 transition-colors"
                >
                  Mark Won
                </button>
                <button
                  onClick={() => setShowWonInput(false)}
                  className="text-xs text-gray-400 hover:text-gray-600"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowWonInput(true)}
                className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-full border border-gray-300 text-gray-500 hover:border-green-400 hover:text-green-700 hover:bg-green-50 transition-colors"
              >
                <DollarSign className="w-3 h-3" /> Mark Won
              </button>
            )}
          </>
        )}

        {won && revenue !== null && (
          <span className="flex items-center gap-1 text-xs text-green-700 bg-green-50 border border-green-200 px-2.5 py-1 rounded-full font-medium">
            <DollarSign className="w-3 h-3" />
            Won ${revenue.toLocaleString()}
          </span>
        )}
      </div>
    </div>
  )
}
