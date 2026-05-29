'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { BoardHeader } from '@/components/board/BoardHeader'
import { SectionHeader } from '@/components/board/SectionHeader'
import { OpportunityCard } from '@/components/board/OpportunityCard'
import { ChurnCard } from '@/components/board/ChurnCard'
import { RetentionCard } from '@/components/board/RetentionCard'
import { ReactivationCard } from '@/components/board/ReactivationCard'
import { MonthlyOutreachList } from '@/components/board/MonthlyOutreachList'
import { MOCK_BOARD } from '@/lib/mock-data'
import type { BoardData } from '@/types'

export default function BoardPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [board, setBoard] = useState<BoardData | null>(null)
  const [isSyncing, setIsSyncing] = useState(false)
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())

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

  const dismiss = (id: string) => setDismissed(prev => new Set(Array.from(prev).concat(id)))

  if (status === 'loading' || !session) return null

  const data = board ?? MOCK_BOARD
  const isDemo = !data.isGmailConnected

  const opportunities = data.opportunities.filter(o => !dismissed.has(o.id))
  const churnSignals = data.churnSignals.filter(c => !dismissed.has(c.id))
  const retentionInsights = data.retentionInsights.filter(r => !dismissed.has(r.id))
  const reactivationTargets = data.reactivationTargets.filter(rv => !dismissed.has(rv.id))

  return (
    <div className="min-h-screen bg-gray-50">
      <BoardHeader
        summary={data.summary}
        isConnected={data.isGmailConnected}
        lastSyncAt={data.lastSyncAt}
        userEmail={session.user?.email ?? ''}
        onSync={handleSync}
        isSyncing={isSyncing}
        isDemo={isDemo}
      />

      <main className="max-w-5xl mx-auto px-4 py-8 space-y-10">

        {/* ── OPPORTUNITIES ── */}
        <section>
          <div className="flex items-center justify-between mb-1">
            <SectionHeader emoji="💰" title="NEW OPPORTUNITIES" count={opportunities.length} subtitle="Leads, quotes, proposals detected in your inbox" />
          </div>
          {opportunities.length === 0
            ? <EmptyState msg="No new opportunities found yet" sub="Sync Gmail to detect leads and proposals" />
            : <div className="space-y-3">{opportunities.map(op => <OpportunityCard key={op.id} op={op} onDismiss={() => dismiss(op.id)} />)}</div>}
        </section>

        <Divider />

        {/* ── CHURN RISKS ── */}
        <section>
          <SectionHeader emoji="🚨" title="CHURN RISKS" count={churnSignals.length} subtitle="Clients showing signs they may leave" />
          {churnSignals.length === 0
            ? <EmptyState msg="No churn risks detected" sub="Your client relationships look healthy" />
            : <div className="space-y-3">{churnSignals.map(c => <ChurnCard key={c.id} signal={c} onResolve={() => dismiss(c.id)} />)}</div>}
        </section>

        <Divider />

        {/* ── RETENTION ── */}
        <section>
          <SectionHeader emoji="💎" title="RETENTION OPPORTUNITIES" count={retentionInsights.length} subtitle="Ways to strengthen existing client relationships" />
          {retentionInsights.length === 0
            ? <EmptyState msg="No retention insights yet" sub="Connect Gmail to surface client relationship opportunities" />
            : <div className="space-y-3">{retentionInsights.map(r => <RetentionCard key={r.id} insight={r} onDismiss={() => dismiss(r.id)} />)}</div>}
        </section>

        <Divider />

        {/* ── REACTIVATION ── */}
        <section>
          <SectionHeader emoji="🔄" title="REACTIVATION TARGETS" count={reactivationTargets.length} subtitle="Old clients and inactive leads worth re-engaging" />
          {reactivationTargets.length === 0
            ? <EmptyState msg="No reactivation targets found" sub="Past clients will appear here after Gmail sync" />
            : <div className="space-y-3">{reactivationTargets.map(rv => <ReactivationCard key={rv.id} target={rv} onSkip={() => dismiss(rv.id)} />)}</div>}
        </section>

        <Divider />

        {/* ── MONTHLY OUTREACH ── */}
        <section>
          <SectionHeader emoji="📋" title="MONTHLY OUTREACH LIST" count={20} subtitle="Top 20 contacts to reach out to this month — with personalized messages" />
          <MonthlyOutreachList />
        </section>

      </main>
    </div>
  )
}

function Divider() {
  return <div className="border-t border-gray-200" />
}

function EmptyState({ msg, sub }: { msg: string; sub: string }) {
  return (
    <div className="bg-white border border-dashed border-gray-200 rounded-xl p-8 text-center">
      <p className="text-gray-500 font-medium">{msg}</p>
      <p className="text-gray-400 text-sm mt-1">{sub}</p>
    </div>
  )
}
