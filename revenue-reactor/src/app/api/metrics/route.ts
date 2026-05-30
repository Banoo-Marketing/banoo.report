import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'
import type { PrecisionMetrics } from '@/types'

function pct(n: number, total: number): number {
  if (total === 0) return 0
  return Math.round((n / total) * 100)
}

function sumValues(vals: (string | null)[]): number {
  let total = 0
  for (const v of vals) {
    const m = v?.match(/\$?([\d,]+)/)
    if (m) total += parseInt(m[1].replace(/,/g, ''), 10)
  }
  return total
}

export async function GET() {
  const { session, error } = await requireSession()
  if (error) return error

  const userId = session!.user.id

  const [opportunities, churnSignals, reactivationTargets, allFeedback] = await Promise.all([
    prisma.opportunity.findMany({ where: { userId } }),
    prisma.churnSignal.findMany({ where: { userId } }),
    prisma.reactivationTarget.findMany({ where: { userId } }),
    prisma.signalFeedback.findMany({ where: { userId } }),
  ])

  const feedbackByKey = new Map(allFeedback.map(f => [`${f.signalType}:${f.signalId}`, f.feedback]))

  const oppWithEvidence = opportunities.filter(o => o.evidence.length > 0)
  const oppGood = opportunities.filter(o => feedbackByKey.get(`opportunity:${o.id}`) === 'useful').length
  const oppBad = opportunities.filter(o => feedbackByKey.get(`opportunity:${o.id}`) === 'not_useful').length
  const oppWon = opportunities.filter(o => o.status === 'won')
  const oppContacted = opportunities.filter(o => ['contacted', 'won'].includes(o.status)).length
  const revenueRecovered = sumValues(oppWon.map(o => o.estimatedValue))

  const churnConfirmed = churnSignals.filter(c =>
    feedbackByKey.get(`churn:${c.id}`) === 'useful' || ['contacted', 'resolved'].includes(c.status)
  ).length
  const churnResolved = churnSignals.filter(c => c.status === 'resolved').length

  const rvContacted = reactivationTargets.filter(rv =>
    ['contacted', 'converted'].includes(rv.status)
  ).length
  const rvConverted = reactivationTargets.filter(rv => rv.status === 'converted').length

  const metrics: PrecisionMetrics = {
    opportunities: {
      total: opportunities.length,
      withEvidence: oppWithEvidence.length,
      goodFinds: oppGood,
      notUseful: oppBad,
      goodFindsPct: pct(oppGood, oppGood + oppBad),
      won: oppWon.length,
      lost: opportunities.filter(o => o.status === 'lost').length,
      contacted: oppContacted,
      revenueRecovered: revenueRecovered > 0 ? `$${revenueRecovered.toLocaleString()}` : '—',
    },
    churn: {
      total: churnSignals.length,
      confirmed: churnConfirmed,
      confirmedPct: pct(churnConfirmed, churnSignals.length),
      resolved: churnResolved,
    },
    reactivation: {
      total: reactivationTargets.length,
      contacted: rvContacted,
      contactedPct: pct(rvContacted, reactivationTargets.length),
      converted: rvConverted,
    },
  }

  return NextResponse.json(metrics)
}
