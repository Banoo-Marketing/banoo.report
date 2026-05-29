'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { signOut } from 'next-auth/react'
import { Search, LogOut, Zap } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { RevenueMetrics } from '@/components/dashboard/RevenueMetrics'
import { OpportunitiesTab } from '@/components/dashboard/OpportunitiesTab'
import { FollowUpsTab } from '@/components/dashboard/FollowUpsTab'
import { AtRiskTab } from '@/components/dashboard/AtRiskTab'
import { ReactivationTab } from '@/components/dashboard/ReactivationTab'
import { MOCK_METRICS } from '@/lib/mock-data'

interface DashboardData {
  totalOpportunities: number
  estimatedRevenue: string
  followUpsNeeded: number
  churnRisks: number
  reactivationTargets: number
  lastSyncAt: string | null
  isGmailConnected: boolean
}

export default function DashboardPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [metrics, setMetrics] = useState<DashboardData | null>(null)
  const [isSyncing, setIsSyncing] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<{ opportunities: unknown[]; churn: unknown[]; reactivations: unknown[] } | null>(null)

  useEffect(() => {
    if (status === 'unauthenticated') router.push('/login')
  }, [status, router])

  const loadMetrics = useCallback(async () => {
    try {
      const res = await fetch('/api/dashboard')
      if (res.ok) {
        const data = await res.json()
        setMetrics(data.data)
      }
    } catch {
      setMetrics(MOCK_METRICS as DashboardData)
    }
  }, [])

  useEffect(() => {
    if (status === 'authenticated') loadMetrics()
  }, [status, loadMetrics])

  const handleSync = async () => {
    setIsSyncing(true)
    try {
      await fetch('/api/gmail/sync', { method: 'POST' })
      await loadMetrics()
    } finally {
      setIsSyncing(false)
    }
  }

  const handleSearch = async (query: string) => {
    setSearchQuery(query)
    if (query.length < 2) {
      setSearchResults(null)
      return
    }
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`)
    if (res.ok) {
      const data = await res.json()
      setSearchResults(data.data)
    }
  }

  if (status === 'loading' || !session) return null

  const isDemo = !metrics?.isGmailConnected
  const displayMetrics = metrics ?? MOCK_METRICS as DashboardData

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-blue-600" />
            <span className="font-bold text-gray-900">Revenue Radar</span>
          </div>
          <div className="flex-1 max-w-md mx-8">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search opportunities, clients..."
                className="w-full pl-9 pr-4 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={searchQuery}
                onChange={e => handleSearch(e.target.value)}
              />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-600">{session.user?.email}</span>
            <Button variant="ghost" size="sm" onClick={() => signOut({ callbackUrl: '/login' })}>
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {isDemo && (
          <div className="mb-6 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl p-5 flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-lg">Connect your Gmail to get started</h3>
              <p className="text-blue-100 text-sm mt-1">We&apos;ll analyze your inbox and surface revenue opportunities in minutes</p>
            </div>
            <Button
              className="bg-white text-blue-700 hover:bg-blue-50 shrink-0 ml-4"
              onClick={handleSync}
            >
              Connect Gmail & Sync
            </Button>
          </div>
        )}

        <div className="mb-8">
          <RevenueMetrics
            totalOpportunities={displayMetrics.totalOpportunities}
            estimatedRevenue={displayMetrics.estimatedRevenue}
            followUpsNeeded={displayMetrics.followUpsNeeded}
            churnRisks={displayMetrics.churnRisks}
            reactivationTargets={displayMetrics.reactivationTargets}
            lastSyncAt={displayMetrics.lastSyncAt}
            isGmailConnected={displayMetrics.isGmailConnected}
            onSync={handleSync}
            isSyncing={isSyncing}
          />
        </div>

        <Tabs defaultValue="opportunities" className="space-y-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="opportunities">
              Revenue Opportunities
              {displayMetrics.totalOpportunities > 0 && (
                <span className="ml-2 bg-blue-600 text-white text-xs rounded-full px-1.5 py-0.5">
                  {displayMetrics.totalOpportunities}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="followups">
              Follow-ups
              {displayMetrics.followUpsNeeded > 0 && (
                <span className="ml-2 bg-amber-500 text-white text-xs rounded-full px-1.5 py-0.5">
                  {displayMetrics.followUpsNeeded}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="atrisk">
              At Risk
              {displayMetrics.churnRisks > 0 && (
                <span className="ml-2 bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5">
                  {displayMetrics.churnRisks}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="reactivation">
              Reactivation
              {displayMetrics.reactivationTargets > 0 && (
                <span className="ml-2 bg-purple-600 text-white text-xs rounded-full px-1.5 py-0.5">
                  {displayMetrics.reactivationTargets}
                </span>
              )}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="opportunities">
            <OpportunitiesTab isDemo={isDemo} />
          </TabsContent>
          <TabsContent value="followups">
            <FollowUpsTab isDemo={isDemo} />
          </TabsContent>
          <TabsContent value="atrisk">
            <AtRiskTab isDemo={isDemo} />
          </TabsContent>
          <TabsContent value="reactivation">
            <ReactivationTab isDemo={isDemo} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
