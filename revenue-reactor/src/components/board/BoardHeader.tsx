'use client'

import { RefreshCw, Zap, LogOut, BarChart2 } from 'lucide-react'
import { signOut } from 'next-auth/react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { timeAgo } from '@/lib/utils'
import type { BoardSummary } from '@/types'

interface Props {
  summary: BoardSummary
  isConnected: boolean
  lastSyncAt: string | null
  userEmail: string
  userName: string | null
  onSync: () => void
  isSyncing: boolean
  isDemo: boolean
}

export function BoardHeader({ summary, isConnected, lastSyncAt, userEmail, userName, onSync, isSyncing, isDemo }: Props) {
  const firstName = userName?.split(' ')[0] ?? userEmail.split('@')[0]
  const hasRevenue = summary.estimatedRevenue !== '—'
  const totalActions = summary.opportunityCount + summary.churnCount + summary.reactivationCount

  return (
    <div className="bg-gradient-to-br from-slate-900 to-blue-950 text-white print:hidden">
      <div className="max-w-4xl mx-auto px-6 py-8">

        {/* Top nav */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-2 text-blue-400 text-sm">
            <Zap className="w-4 h-4 text-blue-400" />
            <span className="font-semibold text-white">Revenue Reactor</span>
          </div>
          <div className="flex items-center gap-1">
            {lastSyncAt && <span className="text-blue-500 text-xs mr-2 hidden md:inline">{timeAgo(lastSyncAt)}</span>}
            <Link href="/reactivation">
              <Button size="sm" variant="ghost" className="text-blue-400 hover:text-white h-8 px-2 text-xs">
                ⚡ Reactivate
              </Button>
            </Link>
            <Link href="/metrics">
              <Button size="sm" variant="ghost" className="text-blue-400 hover:text-white h-8 w-8 p-0">
                <BarChart2 className="w-4 h-4" />
              </Button>
            </Link>
            <Button onClick={() => signOut({ callbackUrl: '/login' })} size="sm" variant="ghost" className="text-blue-400 hover:text-white h-8 w-8 p-0">
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Morning briefing */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-1">Good morning, {firstName}.</h1>
          <p className="text-blue-300 text-lg">
            {isDemo
              ? 'Here is a demo of what your inbox intelligence looks like.'
              : 'I reviewed your Gmail. Here\'s what needs your attention today.'}
          </p>
        </div>

        {/* Summary stats */}
        <div className="flex flex-wrap gap-3 mb-6">
          {hasRevenue && (
            <StatPill label="Potential Revenue" value={summary.estimatedRevenue} color="green" />
          )}
          <StatPill label="Actions Today" value={String(totalActions)} color="blue" />
          {summary.churnCount > 0 && (
            <StatPill label="Clients At Risk" value={String(summary.churnCount)} color="red" />
          )}
          {summary.reactivationCount > 0 && (
            <StatPill label="To Reactivate" value={String(summary.reactivationCount)} color="purple" />
          )}
        </div>

        {/* Sync / connect */}
        <div className="flex items-center gap-3">
          {isConnected ? (
            <Button
              onClick={onSync}
              disabled={isSyncing}
              size="sm"
              variant="outline"
              className="border-blue-600 text-blue-200 hover:bg-blue-800 hover:text-white"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isSyncing ? 'animate-spin' : ''}`} />
              {isSyncing ? 'Reviewing Gmail...' : 'Sync Gmail'}
            </Button>
          ) : (
            <Button
              onClick={onSync}
              size="sm"
              className="bg-blue-500 hover:bg-blue-400 text-white"
            >
              Connect Gmail to see real data
            </Button>
          )}
          {isDemo && (
            <span className="text-blue-400 text-xs italic">Showing demo data</span>
          )}
        </div>
      </div>
    </div>
  )
}

function StatPill({ label, value, color }: { label: string; value: string; color: 'green' | 'blue' | 'red' | 'purple' }) {
  const colors = {
    green: 'bg-green-500/20 border-green-500/30 text-green-300',
    blue: 'bg-blue-500/20 border-blue-500/30 text-blue-200',
    red: 'bg-red-500/20 border-red-500/30 text-red-300',
    purple: 'bg-purple-500/20 border-purple-500/30 text-purple-300',
  }
  return (
    <div className={`border rounded-xl px-4 py-2 ${colors[color]}`}>
      <p className="text-xs opacity-70 mb-0.5">{label}</p>
      <p className="text-lg font-bold">{value}</p>
    </div>
  )
}
