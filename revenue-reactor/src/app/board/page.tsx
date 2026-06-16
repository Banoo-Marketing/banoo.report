'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { Loader2 } from 'lucide-react'
import { TodayCard } from '@/components/board/TodayCard'
import { MOCK_BOARD } from '@/lib/mock-data'
import type { BoardData } from '@/types'

export default function BoardPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [board, setBoard] = useState<BoardData | null>(null)
  const [isSyncing, setIsSyncing] = useState(false)
  const [isFirstSync, setIsFirstSync] = useState(false)
  const hasAutoSynced = useRef(false)

  useEffect(() => {
    if (status === 'unauthenticated') router.push('/login')
  }, [status, router])

  const loadBoard = useCallback(async () => {
    try {
      const res = await fetch('/api/board')
      if (res.ok) {
        const data = await res.json() as BoardData
        setBoard(data)
        return data
      }
    } catch { /* fall through */ }
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
      runSync()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [board])

  const runSync = async () => {
    setIsSyncing(true)
    try {
      await fetch('/api/gmail/sync', { method: 'POST' })
      await loadBoard()
    } finally {
      setIsSyncing(false)
      setIsFirstSync(false)
    }
  }

  if (status === 'loading' || !session) return null

  if (isFirstSync && isSyncing) {
    return (
      <div className="min-h-screen bg-white flex flex-col items-center justify-center gap-4">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        <p className="text-gray-600 font-medium">Reading your inbox...</p>
      </div>
    )
  }

  const data = board ?? MOCK_BOARD
  const isDemo = !data.isGmailConnected
  const actions = data.topActions.slice(0, 3)
  const lastSync = data.lastSyncAt ? new Date(data.lastSyncAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : null

  return (
    <div className="min-h-screen bg-white">
      {/* Top bar */}
      <div className="border-b border-gray-100 px-5 py-3 flex items-center justify-between">
        <span className="font-semibold text-gray-900 text-sm">Revenue Reactor</span>
        <div className="flex items-center gap-3">
          {lastSync && <span className="text-xs text-gray-400">synced {lastSync}</span>}
          <button
            onClick={runSync}
            disabled={isSyncing}
            className="flex items-center gap-1.5 text-xs font-semibold bg-gray-900 text-white px-3 py-1.5 rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50"
          >
            {isSyncing && <Loader2 className="w-3 h-3 animate-spin" />}
            {isSyncing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {isDemo && (
        <div className="bg-blue-50 border-b border-blue-100 px-5 py-2 text-center text-xs text-blue-600">
          Demo mode — <a href="/login" className="font-semibold underline">connect Gmail</a> to see real opportunities
        </div>
      )}

      <main className="max-w-2xl mx-auto px-5 py-10">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">TODAY — DO THESE 3 THINGS</h1>
          <p className="text-gray-400 text-sm mt-1">Ranked by revenue impact. Do these first.</p>
        </div>

        {actions.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-gray-500 font-medium">No high-confidence actions today.</p>
            <p className="text-gray-400 text-sm mt-1">
              {data.isGmailConnected
                ? 'Click Refresh to scan for new signals.'
                : 'Connect Gmail to see real recommendations.'}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {actions.map((action) => (
              <TodayCard key={action.id} action={action} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
