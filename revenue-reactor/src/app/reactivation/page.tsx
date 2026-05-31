'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { Loader2, RefreshCw, Mail, CheckCircle2, Clock, AlertCircle } from 'lucide-react'
import type { ScanContact } from '@/app/api/reactivation/scan/route'

interface FollowUp {
  id: string
  contactName: string
  email: string
  subject: string
  daysSince: number
  status: string
  score: number
  followUp: 'day3' | 'day7' | 'day14' | null
}

interface DraftResult {
  email: string
  name: string
  subject: string
  draftId: string
}

const INTENT_COLOR = {
  high: 'bg-red-100 text-red-700',
  medium: 'bg-yellow-100 text-yellow-700',
  low: 'bg-gray-100 text-gray-600',
}

const FOLLOW_UP_LABEL = {
  day3: { label: 'Day 3 — nudge', color: 'bg-blue-100 text-blue-700' },
  day7: { label: 'Day 7 — soft bump', color: 'bg-orange-100 text-orange-700' },
  day14: { label: 'Day 14 — close loop', color: 'bg-red-100 text-red-700' },
}

export default function ReactivationPage() {
  const { status } = useSession()
  const router = useRouter()

  const [scanning, setScanning] = useState(false)
  const [contacts, setContacts] = useState<ScanContact[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [drafting, setDrafting] = useState(false)
  const [created, setCreated] = useState<DraftResult[]>([])
  const [followUps, setFollowUps] = useState<FollowUp[]>([])
  const [scannedCount, setScannedCount] = useState(0)
  const [error, setError] = useState('')

  useEffect(() => {
    if (status === 'unauthenticated') router.push('/login')
  }, [status, router])

  const loadFollowUps = useCallback(async () => {
    try {
      const res = await fetch('/api/reactivation/follow-ups')
      if (res.ok) {
        const data = await res.json() as { needsFollowUp: FollowUp[] }
        setFollowUps(data.needsFollowUp)
      }
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    if (status === 'authenticated') loadFollowUps()
  }, [status, loadFollowUps])

  async function scan() {
    setScanning(true)
    setError('')
    setContacts([])
    setSelected(new Set())
    try {
      const res = await fetch('/api/reactivation/scan')
      if (!res.ok) throw new Error('Scan failed')
      const data = await res.json() as { contacts: ScanContact[]; scannedThreads: number }
      setContacts(data.contacts)
      setScannedCount(data.scannedThreads)
    } catch {
      setError('Scan failed — make sure Gmail is connected.')
    } finally {
      setScanning(false)
    }
  }

  function toggleSelect(email: string) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(email)) next.delete(email)
      else next.add(email)
      return next
    })
  }

  function selectAll() {
    if (selected.size === contacts.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(contacts.map(c => c.email)))
    }
  }

  async function createDrafts() {
    const picked = contacts.filter(c => selected.has(c.email))
    if (!picked.length) return
    setDrafting(true)
    setError('')
    try {
      const res = await fetch('/api/reactivation/batch-draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contacts: picked }),
      })
      if (!res.ok) throw new Error('Draft creation failed')
      const data = await res.json() as { created: DraftResult[]; failed: unknown[] }
      setCreated(prev => [...data.created, ...prev])
      setSelected(new Set())
      await loadFollowUps()
    } catch {
      setError('Failed to create drafts. Check Gmail connection.')
    } finally {
      setDrafting(false)
    }
  }

  async function markFollowUp(id: string, day: 3 | 7 | 14) {
    await fetch('/api/reactivation/follow-ups', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, followUpDay: day }),
    })
    await loadFollowUps()
  }

  async function markStatus(id: string, status: string) {
    await fetch('/api/reactivation/follow-ups', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, status }),
    })
    await loadFollowUps()
  }

  if (status === 'loading') {
    return <div className="min-h-screen flex items-center justify-center"><Loader2 className="animate-spin" /></div>
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <div className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">⚡ Reactivation Engine</h1>
          <p className="text-xs text-gray-400 mt-0.5">Forgotten money in your inbox — surfaced daily</p>
        </div>
        <a href="/board" className="text-xs text-gray-500 hover:text-gray-300 transition-colors">← Board</a>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-8 space-y-8">

        {/* Follow-ups needing action */}
        {followUps.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-widest mb-3">
              🔔 Needs Follow-Up ({followUps.length})
            </h2>
            <div className="space-y-2">
              {followUps.map(f => (
                <div key={f.id} className="bg-gray-900 border border-gray-700 rounded-lg p-4 flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm">{f.contactName}</span>
                      <span className="text-gray-500 text-xs">{f.email}</span>
                      {f.followUp && (
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${FOLLOW_UP_LABEL[f.followUp].color}`}>
                          {FOLLOW_UP_LABEL[f.followUp].label}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-1 truncate">{f.subject}</p>
                    <p className="text-xs text-gray-600 mt-0.5">{f.daysSince} days since drafted</p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {f.followUp && (
                      <button
                        onClick={() => markFollowUp(f.id, parseInt(f.followUp!.replace('day', '')) as 3 | 7 | 14)}
                        className="text-xs bg-blue-900 hover:bg-blue-800 text-blue-200 px-2 py-1 rounded transition-colors"
                      >
                        Draft follow-up
                      </button>
                    )}
                    <button
                      onClick={() => markStatus(f.id, 'replied')}
                      className="text-xs text-green-400 hover:text-green-300 px-2 py-1 rounded transition-colors"
                      title="Mark replied"
                    >
                      <CheckCircle2 size={14} />
                    </button>
                    <button
                      onClick={() => markStatus(f.id, 'closed')}
                      className="text-xs text-gray-500 hover:text-gray-400 px-2 py-1 rounded transition-colors"
                      title="Close loop"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Scan section */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-widest">
              💰 Today&apos;s Money List
            </h2>
            <button
              onClick={scan}
              disabled={scanning}
              className="flex items-center gap-1.5 bg-white text-gray-900 text-sm font-semibold px-4 py-2 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50"
            >
              {scanning ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
              {scanning ? 'Scanning Gmail…' : 'Scan Gmail'}
            </button>
          </div>

          {error && (
            <div className="flex items-center gap-2 bg-red-900/30 border border-red-800 text-red-300 text-sm px-4 py-2 rounded-lg mb-3">
              <AlertCircle size={14} /> {error}
            </div>
          )}

          {scanning && (
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
              <Loader2 className="animate-spin mx-auto mb-3 text-gray-500" />
              <p className="text-sm text-gray-400">Scanning inbox for dormant opportunities…</p>
            </div>
          )}

          {!scanning && contacts.length > 0 && (
            <>
              <p className="text-xs text-gray-500 mb-3">
                Scanned {scannedCount} threads — found {contacts.length} warm contacts
              </p>
              <div className="space-y-2">
                {contacts.map((c, i) => (
                  <div
                    key={c.email}
                    onClick={() => toggleSelect(c.email)}
                    className={`relative bg-gray-900 border rounded-lg p-4 cursor-pointer transition-all ${
                      selected.has(c.email)
                        ? 'border-white ring-1 ring-white'
                        : 'border-gray-700 hover:border-gray-500'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3 flex-1 min-w-0">
                        <span className="text-xs text-gray-600 w-4 shrink-0 mt-0.5">{i + 1}</span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-medium text-sm">{c.name}</span>
                            <span className="text-gray-500 text-xs">{c.email}</span>
                            <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${INTENT_COLOR[c.intentLevel]}`}>
                              {c.intentLevel.toUpperCase()}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 mt-1 truncate">{c.snippet}</p>
                          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                            <span className="text-xs text-gray-600 flex items-center gap-1">
                              <Clock size={11} /> {c.daysSilent}d silent
                            </span>
                            <span className="text-xs text-green-400 font-medium">{c.estimatedValue}</span>
                            <span className="text-xs text-gray-600">{c.reason}</span>
                          </div>
                        </div>
                      </div>
                      <div className={`w-4 h-4 rounded border shrink-0 mt-0.5 flex items-center justify-center ${
                        selected.has(c.email) ? 'bg-white border-white' : 'border-gray-600'
                      }`}>
                        {selected.has(c.email) && <span className="text-gray-900 text-xs font-bold">✓</span>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex items-center gap-3 mt-4">
                <button
                  onClick={selectAll}
                  className="text-xs text-gray-400 hover:text-white transition-colors"
                >
                  {selected.size === contacts.length ? 'Deselect all' : 'Select all'}
                </button>
                {selected.size > 0 && (
                  <button
                    onClick={createDrafts}
                    disabled={drafting}
                    className="flex items-center gap-2 bg-white text-gray-900 text-sm font-semibold px-5 py-2 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50 ml-auto"
                  >
                    {drafting ? <Loader2 size={14} className="animate-spin" /> : <Mail size={14} />}
                    {drafting ? `Creating ${selected.size} drafts…` : `Create ${selected.size} draft${selected.size > 1 ? 's' : ''}`}
                  </button>
                )}
              </div>
            </>
          )}

          {!scanning && contacts.length === 0 && scannedCount > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
              <p className="text-sm text-gray-400">No dormant opportunities found. Inbox looks active.</p>
            </div>
          )}
        </section>

        {/* Created drafts */}
        {created.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-widest mb-3">
              ✅ Drafts Created ({created.length})
            </h2>
            <div className="bg-gray-900 border border-gray-700 rounded-lg divide-y divide-gray-800">
              {created.map((d, i) => (
                <div key={i} className="px-4 py-3 flex items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium">{d.name}</span>
                    <span className="text-gray-500 text-xs ml-2">{d.email}</span>
                    <p className="text-xs text-gray-500 mt-0.5 truncate">{d.subject}</p>
                  </div>
                  <a
                    href="https://mail.google.com/mail/#drafts"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-400 hover:text-blue-300 transition-colors shrink-0"
                  >
                    Open in Gmail →
                  </a>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-600 mt-2">
              Review drafts in Gmail before sending. Follow-up reminders activate automatically.
            </p>
          </section>
        )}

        {/* How it works */}
        {contacts.length === 0 && created.length === 0 && followUps.length === 0 && (
          <section className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h3 className="text-sm font-semibold mb-4">How this works</h3>
            <div className="space-y-3">
              {[
                ['1', 'Scan Gmail', 'Finds warm contacts silent for 14+ days — ranked by revenue potential'],
                ['2', 'Select contacts', 'Pick who you want to re-engage (start with 5–10)'],
                ['3', 'Create drafts', 'AI writes each email. Drafts land in Gmail — you review & send'],
                ['4', 'Follow-up loop', 'Day 3, 7, 14 reminders surface here automatically'],
              ].map(([num, title, desc]) => (
                <div key={num} className="flex gap-3">
                  <span className="text-xs text-gray-600 w-4 shrink-0 mt-0.5">{num}.</span>
                  <div>
                    <span className="text-sm font-medium">{title} </span>
                    <span className="text-xs text-gray-500">— {desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
