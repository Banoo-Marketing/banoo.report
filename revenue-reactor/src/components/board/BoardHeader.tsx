'use client'

import { RefreshCw, Zap, LogOut } from 'lucide-react'
import { signOut } from 'next-auth/react'
import { Button } from '@/components/ui/button'
import { timeAgo } from '@/lib/utils'
import type { BoardSummary } from '@/types'

interface Props {
  summary: BoardSummary
  isConnected: boolean
  lastSyncAt: string | null
  userEmail: string
  onSync: () => void
  isSyncing: boolean
  isDemo: boolean
}

export function BoardHeader({ summary, isConnected, lastSyncAt, userEmail, onSync, isSyncing, isDemo }: Props) {
  return (
    <div className="bg-gradient-to-r from-slate-900 via-blue-950 to-slate-900 text-white">
      <div className="max-w-5xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="bg-blue-500 rounded-xl p-2">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold">Revenue Reactor</h1>
              <p className="text-blue-300 text-xs">Find money hiding in Gmail</p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {summary.estimatedRevenue !== '—' && (
              <span className="text-green-400 font-bold text-lg">{summary.estimatedRevenue} found</span>
            )}
            <span className="text-blue-200 text-sm hidden sm:inline">
              {summary.opportunityCount} leads · {summary.churnCount} at risk · {summary.reactivationCount} to reactivate
            </span>
          </div>

          <div className="flex items-center gap-2">
            {lastSyncAt && <span className="text-blue-400 text-xs hidden md:inline">{timeAgo(lastSyncAt)}</span>}
            {isConnected && (
              <Button onClick={onSync} disabled={isSyncing} size="sm" variant="outline" className="border-blue-400 text-blue-200 hover:bg-blue-800 hover:text-white">
                <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isSyncing ? 'animate-spin' : ''}`} />
                {isSyncing ? 'Syncing...' : 'Sync'}
              </Button>
            )}
            <span className="text-blue-400 text-xs hidden lg:inline">{userEmail}</span>
            <Button onClick={() => signOut({ callbackUrl: '/login' })} size="sm" variant="ghost" className="text-blue-300 hover:text-white">
              <LogOut className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        {isDemo && (
          <div className="mt-3 bg-blue-500/20 border border-blue-500/40 rounded-lg px-3 py-2 text-sm text-blue-200 flex items-center justify-between flex-wrap gap-2">
            <span>Demo mode — showing example data</span>
            <Button onClick={onSync} size="sm" className="bg-blue-500 hover:bg-blue-400 text-white h-7 text-xs">
              Connect Gmail & Get Real Insights
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
