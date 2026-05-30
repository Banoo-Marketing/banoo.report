import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'
import type { RevenuePlan } from '@/types'

function sumEstimatedValues(values: (string | null)[]): number {
  let total = 0
  for (const v of values) {
    const m = v?.match(/\$?([\d,]+)/)
    if (m) total += parseInt(m[1].replace(/,/g, ''), 10)
  }
  return total
}

function fmt(n: number): string {
  return n > 0 ? `$${n.toLocaleString()}` : '—'
}

export async function GET() {
  const { session, error } = await requireSession()
  if (error) return error

  const userId = session!.user.id
  const month = new Date().toISOString().slice(0, 7)

  const [opportunities, churnSignals, reactivationTargets] = await Promise.all([
    prisma.opportunity.findMany({ where: { userId, status: 'new' }, orderBy: { opportunityScore: 'desc' }, take: 10 }),
    prisma.churnSignal.findMany({ where: { userId, status: 'new' }, orderBy: { churnScore: 'desc' }, take: 5 }),
    prisma.reactivationTarget.findMany({ where: { userId, status: 'pending' }, orderBy: { lastContactDate: 'asc' }, take: 10 }),
  ])

  const newRevTotal = sumEstimatedValues(opportunities.map(o => o.estimatedValue))
  // Estimate churn recovery as 3 months of average opportunity value
  const avgOpValue = opportunities.length > 0 ? newRevTotal / opportunities.length : 2000
  const saveRevTotal = churnSignals.length * Math.round(avgOpValue * 1.5)
  // Estimate reactivation as 40% of avg opportunity value per target
  const reactivateTotal = reactivationTargets.length * Math.round(avgOpValue * 0.4)
  const grandTotal = newRevTotal + saveRevTotal + reactivateTotal

  const plan: RevenuePlan = {
    month,
    generatedAt: new Date().toISOString(),
    newRevenue: {
      items: opportunities.map(o => ({
        name: o.contactName,
        company: o.company,
        detail: o.suggestedAction,
        value: o.estimatedValue,
      })),
      estimatedTotal: fmt(newRevTotal),
    },
    saveRevenue: {
      items: churnSignals.map(c => ({
        name: c.clientName,
        company: null,
        detail: c.recommendedAction,
        value: fmt(Math.round(avgOpValue * 1.5)),
      })),
      estimatedTotal: fmt(saveRevTotal),
    },
    reactivateRevenue: {
      items: reactivationTargets.map(rv => ({
        name: rv.contactName,
        company: rv.company,
        detail: rv.suggestedOffer,
        value: fmt(Math.round(avgOpValue * 0.4)),
      })),
      estimatedTotal: fmt(reactivateTotal),
    },
    totalPotential: fmt(grandTotal),
  }

  return NextResponse.json(plan)
}
