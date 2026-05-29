'use client'

import { useState } from 'react'
import { Loader2, Send, Edit3, CheckCircle } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import type { EmailDraftRequest } from '@/types'

interface EmailDraftModalProps {
  open: boolean
  onClose: () => void
  request: EmailDraftRequest | null
  onSent?: () => void
}

interface DraftData {
  id: string
  to: string
  subject: string
  body: string
  tone: string
}

export function EmailDraftModal({ open, onClose, request, onSent }: EmailDraftModalProps) {
  const [step, setStep] = useState<'generating' | 'review' | 'sending' | 'sent'>('generating')
  const [draft, setDraft] = useState<DraftData | null>(null)
  const [editedBody, setEditedBody] = useState('')
  const [editedSubject, setEditedSubject] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const generateDraft = async () => {
    if (!request) return
    setStep('generating')
    setError(null)

    try {
      const res = await fetch('/api/email/draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.error ?? 'Failed to generate draft')

      const d = data.data as DraftData
      setDraft(d)
      setEditedBody(d.body)
      setEditedSubject(d.subject)
      setStep('review')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate draft')
      setStep('review')
    }
  }

  const handleSend = async () => {
    if (!draft) return
    setStep('sending')

    try {
      const res = await fetch('/api/email/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ draftId: draft.id }),
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.error ?? 'Send failed')
      }

      setStep('sent')
      onSent?.()
      setTimeout(onClose, 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send')
      setStep('review')
    }
  }

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      onClose()
      setTimeout(() => {
        setStep('generating')
        setDraft(null)
        setError(null)
        setIsEditing(false)
      }, 300)
    }
  }

  if (open && step === 'generating' && !draft) {
    generateDraft()
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {step === 'generating' && 'Generating Email Draft...'}
            {step === 'review' && 'Review & Approve Email'}
            {step === 'sending' && 'Sending Email...'}
            {step === 'sent' && 'Email Sent!'}
          </DialogTitle>
        </DialogHeader>

        {step === 'generating' && (
          <div className="flex flex-col items-center justify-center py-12 gap-4">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
            <p className="text-gray-500">Claude is crafting your email...</p>
          </div>
        )}

        {step === 'review' && draft && (
          <div className="space-y-4">
            {error && (
              <div className="bg-red-50 text-red-700 p-3 rounded-md text-sm">{error}</div>
            )}

            <div>
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">To</label>
              <p className="text-sm mt-1 font-medium">{draft.to}</p>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Subject</label>
                {!isEditing && (
                  <button onClick={() => setIsEditing(true)} className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                    <Edit3 className="w-3 h-3" /> Edit
                  </button>
                )}
              </div>
              {isEditing ? (
                <input
                  className="w-full border rounded px-3 py-2 text-sm"
                  value={editedSubject}
                  onChange={e => setEditedSubject(e.target.value)}
                />
              ) : (
                <p className="text-sm border rounded px-3 py-2 bg-gray-50">{editedSubject}</p>
              )}
            </div>

            <div>
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Message</label>
              {isEditing ? (
                <textarea
                  className="w-full border rounded px-3 py-2 text-sm mt-1 h-48 resize-none"
                  value={editedBody}
                  onChange={e => setEditedBody(e.target.value)}
                />
              ) : (
                <pre className="text-sm border rounded px-3 py-2 bg-gray-50 mt-1 whitespace-pre-wrap font-sans h-48 overflow-y-auto">
                  {editedBody}
                </pre>
              )}
            </div>

            <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded p-2">
              ⚠️ Review carefully before sending. This email will be sent from your Gmail account.
            </p>
          </div>
        )}

        {step === 'sending' && (
          <div className="flex flex-col items-center justify-center py-12 gap-4">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
            <p className="text-gray-500">Sending via Gmail...</p>
          </div>
        )}

        {step === 'sent' && (
          <div className="flex flex-col items-center justify-center py-12 gap-4">
            <CheckCircle className="w-8 h-8 text-green-600" />
            <p className="text-gray-700 font-medium">Email sent successfully!</p>
          </div>
        )}

        {step === 'review' && draft && (
          <DialogFooter>
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            {isEditing && (
              <Button variant="outline" onClick={() => setIsEditing(false)}>Done Editing</Button>
            )}
            <Button onClick={handleSend} className="bg-blue-600 hover:bg-blue-700">
              <Send className="w-4 h-4 mr-2" />
              Approve & Send
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}
