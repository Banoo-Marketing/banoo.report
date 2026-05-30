'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { Download, ArrowLeft, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import type { PrecisionMetrics } from '@/types'

function StatCard({ label, value, sub, color = 'gray' }: { label: string; value: string | number; sub?: string; color?: 'gray' | 'green' | 'red' | 'blue' | 'purple' }) {
  const colorMap = {
    gray: 'text-gray-900',
    green: 'text-green-700',
    red: 'text-red-600',
    blue: 'text-blue-700',
    purple: 'text-purple-700',
  }
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-2xl font-bold ${colorMap[color]}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}

export default function MetricsPage() {
  const { status } = useSession()
  const router = useRouter()
  const [metrics, setMetrics] = useState<PrecisionMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    if (status === 'unauthenticated') router.push('/login')
  }, [status, router])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/metrics')
      if (res.ok) setMetrics(await res.json() as PrecisionMetrics)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (status === 'authenticated') load()
  }, [status, load])

  const exportValidation = async () => {
    setExporting(true)
    try {
      const res = await fetch('/api/validation')
      if (!res.ok) return
      const data = await res.json() as Record<string, unknown>
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `revenue-reactor-validation-${new Date().toISOString().slice(0, 10)}.json`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setExporting(false)
    }
  }

  if (status === 'loading') return null

  const opp = metrics?.opportunities
  const churn = metrics?.churn
  const rv = metrics?.reactivation

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/board">
              <Button size="sm" variant="ghost" className="text-gray-500 hover:text-gray-900">
                <ArrowLeft className="w-4 h-4 mr-1.5" />Back
              </Button>
            </Link>
            <h1 className="text-lg font-bold text-gray-900">📊 Precision Dashboard</h1>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={load} disabled={loading}>
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button size="sm" variant="outline" onClick={exportValidation} disabled={exporting}>
              <Download className="w-3.5 h-3.5 mr-1.5" />
              {exporting ? 'Exporting...' : 'Export Validation'}
            </Button>
          </div>
        </div>
      </div>

      <main className="max-w-5xl mx-auto px-4 py-8 space-y-8">
        {loading && !metrics && (
          <div className="text-center py-16 text-gray-400">Loading metrics...</div>
        )}

        {metrics && (
          <>
            {/* Opportunities section */}
            <section>
              <h2 className="text-base font-bold text-gray-900 mb-4">💰 Opportunity Quality</h2>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <StatCard label="Total Found" value={opp?.total ?? 0} color="blue" />
                <StatCard label="With Evidence" value={opp?.withEvidence ?? 0} sub="Required to show" color="blue" />
                <StatCard
                  label="Good Finds %"
                  value={opp && (opp.goodFinds + opp.notUseful) > 0 ? `${opp.goodFindsPct}%` : '—'}
                  sub={opp ? `${opp.goodFinds} good, ${opp.notUseful} not useful` : undefined}
                  color={opp && opp.goodFindsPct >= 60 ? 'green' : 'red'}
                />
                <StatCard label="Bad Finds %" value={opp && (opp.goodFinds + opp.notUseful) > 0 ? `${100 - opp.goodFindsPct}%` : '—'} color="gray" />
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
                <StatCard label="Contacted" value={opp?.contacted ?? 0} color="blue" />
                <StatCard label="Won" value={opp?.won ?? 0} color="green" />
                <StatCard label="Lost" value={opp?.lost ?? 0} color="gray" />
                <StatCard label="Revenue Recovered" value={opp?.revenueRecovered ?? '—'} color="green" />
              </div>
            </section>

            <div className="border-t border-gray-200" />

            {/* Churn section */}
            <section>
              <h2 className="text-base font-bold text-gray-900 mb-4">🚨 Churn Alert Precision</h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <StatCard label="Total Alerts" value={churn?.total ?? 0} color="red" />
                <StatCard
                  label="Confirmed %"
                  value={churn && churn.total > 0 ? `${churn.confirmedPct}%` : '—'}
                  sub={churn ? `${churn.confirmed} of ${churn.total} confirmed` : undefined}
                  color={churn && churn.confirmedPct >= 60 ? 'green' : 'red'}
                />
                <StatCard label="Resolved" value={churn?.resolved ?? 0} color="green" />
              </div>
            </section>

            <div className="border-t border-gray-200" />

            {/* Reactivation section */}
            <section>
              <h2 className="text-base font-bold text-gray-900 mb-4">🔄 Reactivation Performance</h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <StatCard label="Targets Found" value={rv?.total ?? 0} color="purple" />
                <StatCard
                  label="Contacted %"
                  value={rv && rv.total > 0 ? `${rv.contactedPct}%` : '—'}
                  sub={rv ? `${rv.contacted} of ${rv.total} reached` : undefined}
                  color={rv && rv.contactedPct >= 30 ? 'green' : 'gray'}
                />
                <StatCard label="Converted" value={rv?.converted ?? 0} color="green" />
              </div>
            </section>

            <div className="border-t border-gray-200" />

            {/* Signal quality guide */}
            <section>
              <h2 className="text-base font-bold text-gray-900 mb-3">Success Criteria</h2>
              <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-2">
                <QualityCheck
                  label="Opportunity good finds ≥ 60%"
                  pass={opp ? opp.goodFindsPct >= 60 || (opp.goodFinds + opp.notUseful) === 0 : true}
                  note={opp && (opp.goodFinds + opp.notUseful) === 0 ? 'No feedback yet' : undefined}
                />
                <QualityCheck
                  label="Churn alerts confirmed ≥ 50%"
                  pass={churn ? churn.confirmedPct >= 50 || churn.total === 0 : true}
                  note={churn?.total === 0 ? 'No churn alerts yet' : undefined}
                />
                <QualityCheck
                  label="Reactivations contacted ≥ 25%"
                  pass={rv ? rv.contactedPct >= 25 || rv.total === 0 : true}
                  note={rv?.total === 0 ? 'No reactivation targets yet' : undefined}
                />
                <QualityCheck
                  label="Every recommendation has evidence"
                  pass={opp ? opp.withEvidence === opp.total : true}
                />
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  )
}

function QualityCheck({ label, pass, note }: { label: string; pass: boolean; note?: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className={`text-lg ${pass ? 'text-green-500' : 'text-red-500'}`}>
        {pass ? '✓' : '✗'}
      </span>
      <span className="text-sm text-gray-700">{label}</span>
      {note && <span className="text-xs text-gray-400 italic">{note}</span>}
    </div>
  )
}
