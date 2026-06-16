'use client'

import { DollarSign, TrendingUp, AlertTriangle, RefreshCw, Users, Clock } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { timeAgo } from '@/lib/utils'

interface MetricsProps {
  totalOpportunities: number
  estimatedRevenue: string
  followUpsNeeded: number
  churnRisks: number
  reactivationTargets: number
  lastSyncAt: string | Date | null
  isGmailConnected: boolean
  onSync?: () => void
  isSyncing?: boolean
}

export function RevenueMetrics({
  totalOpportunities,
  estimatedRevenue,
  followUpsNeeded,
  churnRisks,
  reactivationTargets,
  lastSyncAt,
  isGmailConnected,
  onSync,
  isSyncing,
}: MetricsProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Revenue Radar</h1>
          <p className="text-gray-500 mt-1">Find money hiding in your Gmail</p>
        </div>
        <div className="flex items-center gap-3">
          {lastSyncAt && (
            <span className="text-sm text-gray-500">
              Last sync: {timeAgo(lastSyncAt)}
            </span>
          )}
          {isGmailConnected && (
            <Button onClick={onSync} disabled={isSyncing} size="sm" variant="outline">
              <RefreshCw className={`w-4 h-4 mr-2 ${isSyncing ? 'animate-spin' : ''}`} />
              {isSyncing ? 'Syncing...' : 'Sync Now'}
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="border-green-200 bg-green-50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-green-700 mb-1">
              <DollarSign className="w-4 h-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Revenue Found</span>
            </div>
            <div className="text-2xl font-bold text-green-800">{estimatedRevenue}</div>
          </CardContent>
        </Card>

        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-blue-700 mb-1">
              <TrendingUp className="w-4 h-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Opportunities</span>
            </div>
            <div className="text-2xl font-bold text-blue-800">{totalOpportunities}</div>
          </CardContent>
        </Card>

        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-yellow-700 mb-1">
              <Clock className="w-4 h-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Follow-ups</span>
            </div>
            <div className="text-2xl font-bold text-yellow-800">{followUpsNeeded}</div>
          </CardContent>
        </Card>

        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-red-700 mb-1">
              <AlertTriangle className="w-4 h-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Churn Risks</span>
            </div>
            <div className="text-2xl font-bold text-red-800">{churnRisks}</div>
          </CardContent>
        </Card>

        <Card className="border-purple-200 bg-purple-50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-purple-700 mb-1">
              <Users className="w-4 h-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Reactivations</span>
            </div>
            <div className="text-2xl font-bold text-purple-800">{reactivationTargets}</div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
