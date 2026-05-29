import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'
import type { BoardData } from '@/types'

export async function GET() {
  const { session, error } = await requireSession()
  if (error) return error

  const userId = session!.user.id

  const [token, opportunities, churnSignals, retentionInsights, reactivationTargets] = await Promise.all([
    prisma.gmailToken.findUnique({ where: { userId } }),
    prisma.opportunity.findMany({ where: { userId, status: 'new' }, orderBy: { opportunityScore: 'desc' }, take: 10 }),
    prisma.churnSignal.findMany({ where: { userId, status: 'new' }, orderBy: { churnScore: 'desc' }, take: 3 }),
    prisma.retentionInsight.findMany({ where: { userId, status: 'new' }, orderBy: { createdAt: 'desc' }, take: 5 }),
    prisma.reactivationTarget.findMany({ where: { userId, status: 'pending' }, orderBy: { lastContactDate: 'asc' }, take: 10 }),
  ])

  let estimatedRevenue = 0
  for (const op of opportunities) {
    const m = op.estimatedValue?.match(/\$?([\d,]+)/)
    if (m) estimatedRevenue += parseInt(m[1].replace(/,/g, ''), 10)
  }

  const data: BoardData = {
    isGmailConnected: !!token,
    lastSyncAt: token?.lastSyncAt?.toISOString() ?? null,
    opportunities: opportunities.map(o => ({
      id: o.id,
      contactName: o.contactName,
      company: o.company,
      opportunityScore: o.opportunityScore,
      estimatedValue: o.estimatedValue,
      reason: o.reason,
      evidence: o.evidence,
      suggestedAction: o.suggestedAction,
      status: o.status,
      createdAt: o.createdAt.toISOString(),
    })),
    churnSignals: churnSignals.map(c => ({
      id: c.id,
      clientName: c.clientName,
      churnScore: c.churnScore,
      riskLevel: c.riskLevel,
      reasons: c.reasons,
      recommendedAction: c.recommendedAction,
      status: c.status,
      createdAt: c.createdAt.toISOString(),
    })),
    retentionInsights: retentionInsights.map(r => ({
      id: r.id,
      clientName: r.clientName,
      insight: r.insight,
      suggestedMessage: r.suggestedMessage,
      timing: r.timing,
      status: r.status,
      createdAt: r.createdAt.toISOString(),
    })),
    reactivationTargets: reactivationTargets.map(rv => ({
      id: rv.id,
      contactName: rv.contactName,
      email: rv.email,
      company: rv.company,
      lastContactDate: rv.lastContactDate.toISOString(),
      history: rv.history,
      suggestedOffer: rv.suggestedOffer,
      suggestedMessage: rv.suggestedMessage,
      status: rv.status,
    })),
    summary: {
      estimatedRevenue: estimatedRevenue > 0 ? `$${estimatedRevenue.toLocaleString()}` : '—',
      opportunityCount: opportunities.length,
      churnCount: churnSignals.length,
      retentionCount: retentionInsights.length,
      reactivationCount: reactivationTargets.length,
    },
  }

  return NextResponse.json(data)
}
