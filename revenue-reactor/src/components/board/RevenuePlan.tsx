'use client'

import { useState } from 'react'
import { Loader2, Printer, Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { RevenuePlan } from '@/types'

export function RevenuePlanSection() {
  const [plan, setPlan] = useState<RevenuePlan | null>(null)
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)

  const load = async () => {
    if (loaded) return
    setLoading(true)
    setLoaded(true)
    try {
      const res = await fetch('/api/revenue-plan')
      if (res.ok) setPlan(await res.json() as RevenuePlan)
    } finally {
      setLoading(false)
    }
  }

  const download = () => {
    if (!plan) return
    const lines = [
      `MONTHLY REVENUE PLAN — ${plan.month}`,
      `Generated: ${new Date(plan.generatedAt).toLocaleDateString()}`,
      '',
      '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
      '💰 NEW REVENUE OPPORTUNITIES',
      '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
      ...plan.newRevenue.items.map((it, i) =>
        `${i + 1}. ${it.name}${it.company ? ` (${it.company})` : ''}\n   Action: ${it.detail}\n   Value: ${it.value ?? 'TBD'}`
      ),
      `   SUBTOTAL: ${plan.newRevenue.estimatedTotal}`,
      '',
      '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
      '🛡 SAVE REVENUE (Churn Prevention)',
      '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
      ...plan.saveRevenue.items.map((it, i) =>
        `${i + 1}. ${it.name}\n   Action: ${it.detail}\n   Est. Value: ${it.value ?? 'TBD'}`
      ),
      `   SUBTOTAL: ${plan.saveRevenue.estimatedTotal}`,
      '',
      '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
      '🔄 REACTIVATE REVENUE',
      '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
      ...plan.reactivateRevenue.items.map((it, i) =>
        `${i + 1}. ${it.name}${it.company ? ` (${it.company})` : ''}\n   Offer: ${it.detail}\n   Est. Value: ${it.value ?? 'TBD'}`
      ),
      `   SUBTOTAL: ${plan.reactivateRevenue.estimatedTotal}`,
      '',
      '═══════════════════════════════════════',
      `TOTAL REVENUE POTENTIAL: ${plan.totalPotential}`,
      '═══════════════════════════════════════',
    ]
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `revenue-plan-${plan.month}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (!loaded) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6 text-center">
        <p className="text-gray-500 text-sm mb-3">See your total revenue opportunity for this month</p>
        <Button onClick={load} className="bg-green-600 hover:bg-green-700">
          Generate Monthly Revenue Plan
        </Button>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-8 flex items-center justify-center gap-3">
        <Loader2 className="w-5 h-5 animate-spin text-green-600" />
        <span className="text-gray-500 text-sm">Building your revenue plan...</span>
      </div>
    )
  }

  if (!plan) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6 text-center">
        <p className="text-gray-500 text-sm">Connect Gmail to generate your monthly revenue plan</p>
      </div>
    )
  }

  return (
    <div id="revenue-plan-print" className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">Generated for {plan.month}</p>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => window.print()} className="h-8 text-xs">
            <Printer className="w-3.5 h-3.5 mr-1.5" />Print
          </Button>
          <Button size="sm" variant="outline" onClick={download} className="h-8 text-xs">
            <Download className="w-3.5 h-3.5 mr-1.5" />Download
          </Button>
        </div>
      </div>

      {/* Total banner */}
      <div className="bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-xl p-4 text-center">
        <p className="text-sm font-medium opacity-90">Total Revenue Potential This Month</p>
        <p className="text-3xl font-bold mt-1">{plan.totalPotential}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* New Revenue */}
        <PlanCard
          emoji="💰"
          title="New Opportunities"
          total={plan.newRevenue.estimatedTotal}
          color="blue"
          items={plan.newRevenue.items}
        />

        {/* Save Revenue */}
        <PlanCard
          emoji="🛡"
          title="Save Revenue"
          total={plan.saveRevenue.estimatedTotal}
          color="red"
          items={plan.saveRevenue.items}
          detailLabel="Action"
        />

        {/* Reactivate Revenue */}
        <PlanCard
          emoji="🔄"
          title="Reactivate Revenue"
          total={plan.reactivateRevenue.estimatedTotal}
          color="purple"
          items={plan.reactivateRevenue.items}
          detailLabel="Offer"
        />
      </div>
    </div>
  )
}

interface PlanCardProps {
  emoji: string
  title: string
  total: string
  color: 'blue' | 'red' | 'purple'
  items: { name: string; company: string | null; detail: string; value: string | null }[]
  detailLabel?: string
}

const COLOR_MAP = {
  blue: { header: 'bg-blue-50 border-blue-100', total: 'text-blue-700', badge: 'bg-blue-100 text-blue-700' },
  red: { header: 'bg-red-50 border-red-100', total: 'text-red-700', badge: 'bg-red-100 text-red-700' },
  purple: { header: 'bg-purple-50 border-purple-100', total: 'text-purple-700', badge: 'bg-purple-100 text-purple-700' },
}

function PlanCard({ emoji, title, total, color, items, detailLabel = 'Action' }: PlanCardProps) {
  const c = COLOR_MAP[color]
  return (
    <div className={`border rounded-xl overflow-hidden ${c.header}`}>
      <div className={`px-4 py-3 border-b ${c.header}`}>
        <div className="flex items-center justify-between">
          <span className="font-semibold text-gray-900 text-sm">{emoji} {title}</span>
          <span className={`text-lg font-bold ${c.total}`}>{total}</span>
        </div>
      </div>
      <div className="bg-white divide-y divide-gray-50">
        {items.length === 0 && (
          <p className="text-xs text-gray-400 p-3 text-center">None detected</p>
        )}
        {items.map((item, i) => (
          <div key={i} className="px-3 py-2.5">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{item.name}</p>
                {item.company && <p className="text-xs text-gray-500 truncate">{item.company}</p>}
                <p className="text-xs text-gray-600 mt-0.5 line-clamp-2">{detailLabel}: {item.detail}</p>
              </div>
              {item.value && item.value !== '—' && (
                <span className={`text-xs font-semibold px-1.5 py-0.5 rounded shrink-0 ${c.badge}`}>{item.value}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
