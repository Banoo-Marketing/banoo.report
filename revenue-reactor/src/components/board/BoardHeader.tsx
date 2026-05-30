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
  const hasRevenue = summary.estimatedRevenue !== '—'

  return (
    <div className="bg-gradient-to-r from-slate-900 via-blue-950 to-slate-900 text-white print:hidden">
      <div className="max-w-5xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="bg-blue-500 rounded-xl p-2">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold">Revenue Reactor</h1>
              <p className="text-blue-300 text-xs">Your inbox revenue intelligence</p>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            {hasRevenue && (
              <div className="text-right">
                <p className="text-blue-300 text-xs">Revenue Found</p>
                <p className="text-green-400 font-bold text-xl leading-tight">{summary.estimatedRevenue}</p>
              </div>
            )}
            <div className="hidden sm:flex items-center gap-2 text-sm">
              {summary.opportunityCount > 0 && (
                <span className="bg-blue-700/50 text-blue-200 px-2 py-0.5 rounded-full text-xs">
                  {summary.opportunityCount} leads
                </span>
              )}
              {summary.churnCount > 0 && (
                <span className="bg-red-700/50 text-red-200 px-2 py-0.5 rounded-full text-xs">
                  {summary.churnCount} at risk
                </span>
              )}
              {summary.reactivationCount > 0 && (
                <span className="bg-purple-700/50 text-purple-200 px-2 py-0.5 rounded-full text-xs">
                  {summary.reactivationCount} to reactivate
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {lastSyncAt && <span className="text-blue-400 text-xs hidden md:inline">{timeAgo(lastSyncAt)}</span>}
            {isConnected && (
              <Button onClick={onSync} disabled={isSyncing} size="sm" variant="outline" className="border-blue-400 text-blue-200 hover:bg-blue-800 hover:text-white">
                <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isSyncing ? 'animate-spin' : ''}`} />
                {isSyncing ? 'Syncing...' : 'Sync Now'}
              </Button>
            )}
            <span className="text-blue-400 text-xs hidden lg:inline">{userEmail}</span>
            <Button onClick={() => signOut({ callbackUrl: '/login' })} size="sm" variant="ghost" className="text-blue-300 hover:text-white">
              <LogOut className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        {isDemo && (
          <div className="mt-3 bg-blue-500/20 border border-blue-500/40 rounded-lg px-3 py-2.5 flex items-center justify-between flex-wrap gap-2">
            <div>
              <p className="text-sm font-medium text-blue-100">Demo mode — showing example data</p>
              <p className="text-xs text-blue-300">Connect Gmail to see real opportunities from your inbox</p>
            </div>
            <Button onClick={onSync} size="sm" className="bg-blue-500 hover:bg-blue-400 text-white h-8 text-xs">
              Connect Gmail
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
