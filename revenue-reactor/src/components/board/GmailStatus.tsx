'use client'

import { AlertTriangle, CheckCircle2, WifiOff } from 'lucide-react'
import { timeAgo } from '@/lib/utils'
import type { GmailSyncStats } from '@/types'

interface Props {
  connected: boolean
  lastSyncAt: string | null
  syncStats: GmailSyncStats | null
  accuracyScore: number | null
}

export function GmailStatus({ connected, lastSyncAt, syncStats, accuracyScore }: Props) {
  const error = syncStats?.lastSyncError

  if (error) {
    return (
      <div className="bg-amber-50 border-b border-amber-200 px-6 py-2.5">
        <div className="max-w-4xl mx-auto flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
          <p className="text-sm text-amber-800 font-medium">{error}</p>
        </div>
      </div>
    )
  }

  if (!connected) {
    return (
      <div className="bg-gray-100 border-b border-gray-200 px-6 py-2">
        <div className="max-w-4xl mx-auto flex items-center gap-2">
          <WifiOff className="w-3.5 h-3.5 text-gray-400" />
          <p className="text-xs text-gray-500">Gmail not connected — showing demo data</p>
        </div>
      </div>
    )
  }

  const parts: string[] = []
  if (lastSyncAt) parts.push(`Synced ${timeAgo(lastSyncAt)}`)
  if (syncStats?.threadsAnalyzed) parts.push(`${syncStats.threadsAnalyzed.toLocaleString()} conversations reviewed`)
  if (syncStats?.emailsAnalyzed) parts.push(`${syncStats.emailsAnalyzed.toLocaleString()} emails read`)

  return (
    <div className="bg-green-50 border-b border-green-100 px-6 py-2">
      <div className="max-w-4xl mx-auto flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5 text-green-600 shrink-0" />
          <p className="text-xs text-green-800">{parts.length > 0 ? parts.join(' · ') : 'Gmail connected'}</p>
        </div>
        {accuracyScore !== null && (
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
            accuracyScore >= 70 ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
          }`}>
            Accuracy: {accuracyScore}%
          </span>
        )}
      </div>
    </div>
  )
}
