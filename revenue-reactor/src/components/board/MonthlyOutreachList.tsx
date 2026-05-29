'use client'

import { useState } from 'react'
import { Loader2, RefreshCw, Copy, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { OutreachContact } from '@/types'

interface MonthlyList {
  month: string
  contacts: OutreachContact[]
  generatedAt: string
}

export function MonthlyOutreachList() {
  const [list, setList] = useState<MonthlyList | null>(null)
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null)

  const load = async () => {
    if (loaded) return
    setLoading(true)
    setLoaded(true)
    try {
      const res = await fetch('/api/outreach')
      if (res.ok) {
        const data = await res.json() as { data: { month: string; contacts: OutreachContact[]; generatedAt: string } | null }
        if (data.data) setList(data.data)
      }
    } finally {
      setLoading(false)
    }
  }

  const generate = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/outreach', { method: 'POST' })
      if (res.ok) {
        const data = await res.json() as { data: { month: string; contacts: OutreachContact[]; generatedAt: string } }
        setList(data.data)
      }
    } finally {
      setLoading(false)
    }
  }

  const copyMsg = async (contact: OutreachContact, idx: number) => {
    await navigator.clipboard.writeText(`Subject: Following up\n\nHi ${contact.name},\n\n${contact.suggestedMessage}`)
    setCopiedIdx(idx)
    setTimeout(() => setCopiedIdx(null), 1500)
  }

  if (!loaded) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6 text-center">
        <p className="text-gray-500 text-sm mb-3">Load your monthly outreach list</p>
        <Button onClick={load} variant="outline">📋 Load Monthly List</Button>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-8 flex items-center justify-center gap-3">
        <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
        <span className="text-gray-500 text-sm">Generating your personalized outreach list...</span>
      </div>
    )
  }

  if (!list) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6 text-center">
        <p className="text-gray-500 text-sm mb-3">No outreach list for this month yet</p>
        <Button onClick={generate} className="bg-blue-600 hover:bg-blue-700">
          Generate Monthly List (Top 20 Contacts)
        </Button>
      </div>
    )
  }

  const contacts = Array.isArray(list.contacts) ? list.contacts : []

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-gray-500">Month: {list.month} · {contacts.length} contacts</p>
        <Button size="sm" variant="outline" onClick={generate} disabled={loading}>
          <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
          Regenerate
        </Button>
      </div>

      {contacts.map((contact, idx) => (
        <div key={idx} className="bg-white border border-gray-200 rounded-lg p-3 flex items-start gap-3">
          <span className="text-sm font-bold text-gray-400 w-6 shrink-0">#{contact.priority ?? idx + 1}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span className="font-medium text-sm text-gray-900">{contact.name}</span>
              {contact.company && <span className="text-xs text-gray-500">· {contact.company}</span>}
            </div>
            <p className="text-xs text-gray-500 mb-1">{contact.email}</p>
            <p className="text-xs text-gray-600 mb-1">{contact.reason}</p>
            <p className="text-xs bg-gray-50 border rounded px-2 py-1 italic text-gray-700">{contact.suggestedMessage}</p>
          </div>
          <Button size="sm" variant="outline" onClick={() => copyMsg(contact, idx)} className="h-8 shrink-0">
            {copiedIdx === idx ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          </Button>
        </div>
      ))}
    </div>
  )
}
