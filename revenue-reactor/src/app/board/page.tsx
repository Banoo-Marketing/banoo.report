'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { Loader2, X, ChevronDown, ChevronUp } from 'lucide-react'
import { BoardHeader } from '@/components/board/BoardHeader'
import { GmailStatus } from '@/components/board/GmailStatus'
import { TodayCard } from '@/components/board/TodayCard'
import { OpportunityCard } from '@/components/board/OpportunityCard'
import { ChurnCard } from '@/components/board/ChurnCard'
import { ReactivationCard } from '@/components/board/ReactivationCard'
import { MOCK_BOARD } from '@/lib/mock-data'
import type { BoardData } from '@/types'

interface SyncSummary {
  threadsAnalyzed: number
  opportunities: number
  churnRisks: number
  reactivations: number
  estimatedRevenue: string
}

export default function BoardPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [board, setBoard] = useState<BoardData | null>(null)
  const [isSyncing, setIsSyncing] = useState(false)
  const [isFirstSync, setIsFirstSync] = useState(false)
  const [syncSummary, setSyncSummary] = useState<SyncSummary | null>(null)
  const [showMore, setShowMore] = useState(false)
  const hasAutoSynced = useRef(false)

  useEffect(() => {
    if (status === 'unauthenticated') router.push('/login')
  }, [status, router])

  const loadBoard = useCallback(async (): Promise<BoardData | null> => {
    try {
      const res = await fetch('/api/board')
      if (res.ok) {
        const data = await res.json() as BoardData
        setBoard(data)
        return data
      }
    } catch {
      // fall through
    }
    setBoard(MOCK_BOARD)
    return null
  }, [])

  useEffect(() => {
    if (status === 'authenticated') loadBoard()
  }, [status, loadBoard])

  useEffect(() => {
    if (board && board.isGmailConnected && !board.lastSyncAt && !hasAutoSynced.current) {
      hasAutoSynced.current = true
      setIsFirstSync(true)
      runSync(true)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [board])

  const runSync = async (isFirst = false) => {
    setIsSyncing(true)
    try {
      await fetch('/api/gmail/sync', { method: 'POST' })
      const newBoard = await loadBoard()
      if (isFirst && newBoard) {
        setSyncSummary({
          threadsAnalyzed: newBoard.syncStats?.threadsAnalyzed ?? 0,
          opportunities: newBoard.summary.opportunityCount,
          churnRisks: newBoard.summary.churnCount,
          reactivations: newBoard.summary.reactivationCount,
          estimatedRevenue: newBoard.summary.estimatedRevenue,
        })
      }
    } finally {
      setIsSyncing(false)
      setIsFirstSync(false)
    }
  }

  const handleSync = () => runSync(false)

  if (status === 'loading' || !session) return null

  if (isFirstSync && isSyncing) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center gap-6 px-4">
        <Loader2 className="w-10 h-10 animate-spin text-blue-600" />
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Analyzing your inbox...</h2>
          <p className="text-gray-500 max-w-sm">
            Finding opportunities, at-risk clients, and contacts worth reactivating.
          </p>
        </div>
      </div>
    )
  }

  const data = board ?? MOCK_BOARD
  const isDemo = !data.isGmailConnected

  // Execution mode limits
  const topActions = data.topActions.slice(0, 4)
  const moreOpps = data.opportunities.slice(0, 3)
  const moreChurn = data.churnSignals.slice(0, 1)
  const moreReactivation = data.reactivationTargets.slice(0, 3)
  const moreCount = moreOpps.length + moreChurn.length + moreReactivation.length

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

      <GmailStatus
        connected={data.isGmailConnected}
        lastSyncAt={data.lastSyncAt}
        syncStats={data.syncStats}
        accuracyScore={data.accuracyScore}
      />

      {syncSummary && (
        <div className="bg-blue-600 text-white px-6 py-4 print:hidden">
          <div className="max-w-4xl mx-auto flex items-start justify-between gap-4">
            <div>
              <p className="font-semibold text-base">
                {syncSummary.threadsAnalyzed > 0
                  ? `I reviewed ${syncSummary.threadsAnalyzed.toLocaleString()} conversations and found:`
                  : 'Analysis complete. Here\'s what I found:'}
              </p>
              <p className="text-blue-100 text-sm mt-1">
                {[
                  syncSummary.opportunities > 0 && `${syncSummary.opportunities} ${syncSummary.opportunities === 1 ? 'opportunity' : 'opportunities'}`,
                  syncSummary.churnRisks > 0 && `${syncSummary.churnRisks} at-risk ${syncSummary.churnRisks === 1 ? 'client' : 'clients'}`,
                  syncSummary.reactivations > 0 && `${syncSummary.reactivations} reactivation ${syncSummary.reactivations === 1 ? 'target' : 'targets'}`,
                ].filter(Boolean).join(' · ') || 'Nothing significant found — try again after more emails come in.'}
                {syncSummary.estimatedRevenue !== '—' && ` · Estimated revenue: ${syncSummary.estimatedRevenue}`}
              </p>
            </div>
            <button onClick={() => setSyncSummary(null)} className="text-blue-300 hover:text-white shrink-0 mt-0.5">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-6">

        {/* Revenue recovered — only show when non-zero */}
        {(data.revenueRecoveredAllTime !== '$0' || data.revenueRecoveredThisMonth !== '$0') && (
          <div className="flex gap-4">
            <div className="bg-green-50 border border-green-200 rounded-xl px-5 py-3">
              <p className="text-xs text-green-700 font-medium mb-0.5">Recovered This Month</p>
              <p className="text-xl font-bold text-green-800">{data.revenueRecoveredThisMonth}</p>
            </div>
            <div className="bg-green-50 border border-green-200 rounded-xl px-5 py-3">
              <p className="text-xs text-green-700 font-medium mb-0.5">Recovered All Time</p>
              <p className="text-xl font-bold text-green-800">{data.revenueRecoveredAllTime}</p>
            </div>
          </div>
        )}

        {/* EXECUTION MODE — top 3 actions only */}
        <section className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
          <div className="bg-gray-900 px-5 py-4">
            <h2 className="text-white font-bold text-lg tracking-tight">TODAY — DO THESE 4 THINGS</h2>
            <p className="text-gray-400 text-sm mt-0.5">Do these first. Everything else can wait.</p>
          </div>
          <div className="px-5">
            {topActions.length === 0 ? (
              <div className="py-8 text-center">
                <p className="text-gray-500 font-medium">Nothing requires action today.</p>
                <p className="text-gray-400 text-sm mt-1">
                  {data.isGmailConnected
                    ? 'Sync Gmail to check for new signals.'
                    : 'Connect Gmail to see real recommendations.'}
                </p>
              </div>
            ) : (
              topActions.map((action, i) => (
                <TodayCard key={action.id} action={action} rank={i + 1} />
              ))
            )}
          </div>
        </section>

        {/* View more toggle */}
        {moreCount > 0 && (
          <div className="text-center">
            <button
              onClick={() => setShowMore(prev => !prev)}
              className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 transition-colors"
            >
              {showMore ? (
                <><ChevronUp className="w-4 h-4" /> Hide additional signals</>
              ) : (
                <><ChevronDown className="w-4 h-4" /> View {moreCount} additional signal{moreCount !== 1 ? 's' : ''}</>
              )}
            </button>
          </div>
        )}

        {/* Additional signals — hidden by default */}
        {showMore && (
          <>
            {moreOpps.length > 0 && (
              <section>
                <h2 className="text-base font-semibold text-gray-500 uppercase tracking-wide mb-3">
                  More Opportunities
                </h2>
                <div className="space-y-3">
                  {moreOpps.map((op, i) => <OpportunityCard key={op.id} op={op} index={i + 1} />)}
                </div>
              </section>
            )}

            {moreChurn.length > 0 && (
              <section>
                <h2 className="text-base font-semibold text-gray-500 uppercase tracking-wide mb-3">
                  Client At Risk
                </h2>
                <div className="space-y-3">
                  {moreChurn.map((c, i) => <ChurnCard key={c.id} signal={c} index={i + 1} />)}
                </div>
              </section>
            )}

            {moreReactivation.length > 0 && (
              <section>
                <h2 className="text-base font-semibold text-gray-500 uppercase tracking-wide mb-3">
                  Reactivation
                </h2>
                <div className="space-y-3">
                  {moreReactivation.map((rv, i) => <ReactivationCard key={rv.id} target={rv} index={i + 1} />)}
                </div>
              </section>
            )}

            <div className="text-center pt-2">
              <button
                onClick={() => setShowMore(false)}
                className="inline-flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-600 transition-colors"
              >
                <ChevronUp className="w-4 h-4" /> Hide
              </button>
            </div>
          </>
        )}

      </main>
    </div>
  )
}
