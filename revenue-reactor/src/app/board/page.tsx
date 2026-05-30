'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { BoardHeader } from '@/components/board/BoardHeader'
import { OpportunityCard } from '@/components/board/OpportunityCard'
import { ChurnCard } from '@/components/board/ChurnCard'
import { ReactivationCard } from '@/components/board/ReactivationCard'
import { MOCK_BOARD } from '@/lib/mock-data'
import type { BoardData } from '@/types'

export default function BoardPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [board, setBoard] = useState<BoardData | null>(null)
  const [isSyncing, setIsSyncing] = useState(false)

  useEffect(() => {
    if (status === 'unauthenticated') router.push('/login')
  }, [status, router])

  const loadBoard = useCallback(async () => {
    try {
      const res = await fetch('/api/board')
      if (res.ok) setBoard(await res.json() as BoardData)
      else setBoard(MOCK_BOARD)
    } catch {
      setBoard(MOCK_BOARD)
    }
  }, [])

  useEffect(() => {
    if (status === 'authenticated') loadBoard()
  }, [status, loadBoard])

  const handleSync = async () => {
    setIsSyncing(true)
    try {
      await fetch('/api/gmail/sync', { method: 'POST' })
      await loadBoard()
    } finally {
      setIsSyncing(false)
    }
  }

  if (status === 'loading' || !session) return null

  const data = board ?? MOCK_BOARD
  const isDemo = !data.isGmailConnected

  const opportunities = data.opportunities.slice(0, 5)
  const churnSignals = data.churnSignals.slice(0, 3)
  const reactivationTargets = data.reactivationTargets.slice(0, 10)

  return (
    <div className="min-h-screen bg-gray-50">
      <BoardHeader
        summary={data.summary}
        isConnected={data.isGmailConnected}
        lastSyncAt={data.lastSyncAt}
        userEmail={session.user?.email ?? ''}
        userName={session.user?.name ?? null}
        onSync={handleSync}
        isSyncing={isSyncing}
        isDemo={isDemo}
      />

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-8">

        {/* ── CONTACT TODAY ── */}
        <section>
          <SectionTitle emoji="💰" title="New Opportunities" count={opportunities.length} />
          {opportunities.length === 0
            ? <EmptyState msg="No new opportunities right now" sub="Sync Gmail to detect leads, quotes, and proposals" />
            : <div className="space-y-3">{opportunities.map((op, i) => <OpportunityCard key={op.id} op={op} index={i + 1} />)}</div>}
        </section>

        <Divider />

        {/* ── CLIENTS AT RISK ── */}
        <section>
          <SectionTitle emoji="🚨" title="Clients At Risk" count={churnSignals.length} />
          {churnSignals.length === 0
            ? <EmptyState msg="No churn risks detected" sub="Your client relationships look healthy" />
            : <div className="space-y-3">{churnSignals.map((c, i) => <ChurnCard key={c.id} signal={c} index={i + 1} />)}</div>}
        </section>

        <Divider />

        {/* ── REACTIVATE ── */}
        <section>
          <SectionTitle emoji="🔄" title="Reactivation Targets" count={reactivationTargets.length} />
          {reactivationTargets.length === 0
            ? <EmptyState msg="No reactivation targets found" sub="Past clients will appear here after Gmail sync" />
            : <div className="space-y-3">{reactivationTargets.map((rv, i) => <ReactivationCard key={rv.id} target={rv} index={i + 1} />)}</div>}
        </section>

      </main>
    </div>
  )
}

function Divider() {
  return <div className="border-t border-gray-200" />
}

function SectionTitle({ emoji, title, count }: { emoji: string; title: string; count?: number }) {
  return (
    <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
      <span>{emoji}</span>
      {title}
      {count !== undefined && <span className="text-base font-normal text-gray-400">({count})</span>}
    </h2>
  )
}

function EmptyState({ msg, sub }: { msg: string; sub: string }) {
  return (
    <div className="bg-white border border-dashed border-gray-200 rounded-xl p-8 text-center">
      <p className="text-gray-500 font-medium">{msg}</p>
      <p className="text-gray-400 text-sm mt-1">{sub}</p>
    </div>
  )
}
