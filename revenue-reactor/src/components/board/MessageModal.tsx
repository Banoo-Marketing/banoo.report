'use client'

import { useState, useCallback } from 'react'
import { Copy, Check, Loader2 } from 'lucide-react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { callClaude } from './modalHelpers'

interface Props {
  open: boolean
  onClose: () => void
  to: string
  context: string
  signalType: 'opportunity' | 'churn' | 'retention' | 'reactivation'
}

interface Draft { subject: string; body: string }

export function MessageModal({ open, onClose, to, context, signalType }: Props) {
  const [draft, setDraft] = useState<Draft | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [editBody, setEditBody] = useState('')
  const [editSubject, setEditSubject] = useState('')
  const [editing, setEditing] = useState(false)
  const [generated, setGenerated] = useState(false)

  const generate = useCallback(async () => {
    if (generated) return
    setLoading(true)
    setGenerated(true)
    try {
      const d = await callClaude(signalType, to, context)
      setDraft(d)
      setEditBody(d.body)
      setEditSubject(d.subject)
    } catch {
      setDraft({ subject: `Following up`, body: `Hi,\n\nI wanted to reach out about our recent conversation.\n\nBest,` })
      setEditBody(`Hi,\n\nI wanted to reach out about our recent conversation.\n\nBest,`)
      setEditSubject('Following up')
    } finally {
      setLoading(false)
    }
  }, [generated, signalType, to, context])

  if (open && !generated) generate()

  const copy = async () => {
    await navigator.clipboard.writeText(`Subject: ${editSubject}\n\n${editBody}`)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const mailtoLink = `mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(editSubject)}&body=${encodeURIComponent(editBody)}`

  const handleClose = () => {
    onClose()
    setTimeout(() => { setDraft(null); setGenerated(false); setEditing(false); setCopied(false) }, 300)
  }

  return (
    <Dialog open={open} onOpenChange={v => !v && handleClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Email Draft</DialogTitle>
        </DialogHeader>

        {loading && (
          <div className="flex flex-col items-center py-12 gap-3">
            <Loader2 className="w-7 h-7 animate-spin text-blue-600" />
            <p className="text-gray-500 text-sm">Generating personalized message...</p>
          </div>
        )}

        {!loading && draft && (
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">To</label>
              <p className="text-sm mt-1">{to}</p>
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Subject</label>
                {!editing && <button onClick={() => setEditing(true)} className="text-xs text-blue-600 hover:underline">Edit</button>}
              </div>
              {editing
                ? <input className="w-full border rounded px-3 py-2 text-sm" value={editSubject} onChange={e => setEditSubject(e.target.value)} />
                : <p className="text-sm bg-gray-50 border rounded px-3 py-2">{editSubject}</p>}
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Message</label>
              {editing
                ? <textarea className="w-full border rounded px-3 py-2 text-sm mt-1 h-44 resize-none font-mono" value={editBody} onChange={e => setEditBody(e.target.value)} />
                : <pre className="text-sm bg-gray-50 border rounded px-3 py-2 mt-1 h-44 overflow-y-auto whitespace-pre-wrap font-sans">{editBody}</pre>}
            </div>
            {editing && <Button size="sm" variant="outline" onClick={() => setEditing(false)}>Done Editing</Button>}
          </div>
        )}

        {!loading && draft && (
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={handleClose}>Cancel</Button>
            <a href={mailtoLink} target="_blank" rel="noopener noreferrer">
              <Button variant="outline">Open in Gmail</Button>
            </a>
            <Button onClick={copy} className="bg-blue-600 hover:bg-blue-700">
              {copied ? <><Check className="w-4 h-4 mr-2" />Copied!</> : <><Copy className="w-4 h-4 mr-2" />Copy Message</>}
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}
