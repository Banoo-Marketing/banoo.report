import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'
import { buildTopActions } from '@/agents/top-actions-engine'
import type { BoardData, FeedbackValue } from '@/types'

function formatMoney(amount: number): string {
  return amount >= 1000
    ? `$${(amount / 1000).toFixed(amount % 1000 === 0 ? 0 : 1)}k`
    : `$${Math.round(amount).toLocaleString()}`
}

export async function GET() {
  const { session, error } = await requireSession()
  if (error) return error

  const userId = session!.user.id
  const now = new Date()
  const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)

  const [
    token,
    opportunities,
    churnSignals,
    retentionInsights,
    reactivationTargets,
    feedbackRows,
    wonOpportunities,
    contactedChurn,
    contactedReactivation,
  ] = await Promise.all([
    prisma.gmailToken.findUnique({ where: { userId } }),
    prisma.opportunity.findMany({
      where: { userId, status: { in: ['new', 'contacted', 'won'] } },
      orderBy: { opportunityScore: 'desc' },
      take: 20,
    }),
    prisma.churnSignal.findMany({
      where: { userId, status: { in: ['new', 'contacted'] } },
      orderBy: { churnScore: 'desc' },
      take: 5,
    }),
    prisma.retentionInsight.findMany({
      where: { userId, status: 'new' },
      orderBy: { createdAt: 'desc' },
      take: 5,
    }),
    prisma.reactivationTarget.findMany({
      where: { userId, status: { in: ['pending', 'contacted'] } },
      orderBy: { lastContactDate: 'asc' },
      take: 15,
    }),
    prisma.signalFeedback.findMany({ where: { userId } }),
    prisma.opportunity.findMany({
      where: { userId, status: 'won' },
      select: { revenueRecovered: true, revenueWonAt: true },
    }),
    prisma.churnSignal.count({ where: { userId, status: 'contacted' } }),
    prisma.reactivationTarget.count({ where: { userId, status: 'contacted' } }),
  ])

  const feedbackMap = new Map<string, FeedbackValue>(
    feedbackRows.map(f => [`${f.signalType}:${f.signalId}`, f.feedback as FeedbackValue])
  )

  // Confidence filter: require evidence + confidence ≥ 70 + not ignored
  const validOpportunities = opportunities.filter(o =>
    o.evidence.length > 0 &&
    (o.revenueConfidence ?? 0) >= 70 &&
    feedbackMap.get(`opportunity:${o.id}`) !== 'not_useful'
  )

  const validChurn = churnSignals.filter(c =>
    feedbackMap.get(`churn:${c.id}`) !== 'not_useful'
  )

  const validReactivation = reactivationTargets.filter(rv =>
    feedbackMap.get(`reactivation:${rv.id}`) !== 'not_useful'
  )

  // Revenue recovery totals
  const revenueAllTime = wonOpportunities.reduce((sum, o) => sum + (o.revenueRecovered ?? 0), 0)
  const revenueThisMonth = wonOpportunities
    .filter(o => o.revenueWonAt && o.revenueWonAt >= startOfMonth)
    .reduce((sum, o) => sum + (o.revenueRecovered ?? 0), 0)

  // Accuracy: (contacted + won) / (contacted + won + ignored)
  const contactedOpps = opportunities.filter(o => o.status === 'contacted' || o.status === 'won').length
  const goodFinds = contactedOpps + contactedChurn + contactedReactivation
  const notUseful = feedbackRows.filter(f => f.feedback === 'not_useful').length
  const accuracyScore = goodFinds + notUseful >= 3
    ? Math.round((goodFinds / (goodFinds + notUseful)) * 100)
    : null

  // Potential revenue from surfaced opportunities
  let estimatedRevenue = 0
  for (const op of validOpportunities) {
    const m = op.estimatedValue?.match(/\$?([\d,]+)/)
    if (m) estimatedRevenue += parseInt(m[1].replace(/,/g, ''), 10)
  }

  const boardOpportunities = validOpportunities.map(o => ({
    id: o.id,
    contactName: o.contactName,
    company: o.company,
    opportunityScore: o.opportunityScore,
    revenueConfidence: o.revenueConfidence,
    estimatedValue: o.estimatedValue,
    reason: o.reason,
    evidence: o.evidence,
    suggestedAction: o.suggestedAction,
    status: o.status,
    revenueRecovered: o.revenueRecovered ?? null,
    userFeedback: feedbackMap.get(`opportunity:${o.id}`) ?? null,
    createdAt: o.createdAt.toISOString(),
  }))

  const boardChurnSignals = validChurn.map(c => ({
    id: c.id,
    clientName: c.clientName,
    churnScore: c.churnScore,
    riskLevel: c.riskLevel,
    reasons: c.reasons,
    whatHappened: c.whatHappened,
    whyItMatters: c.whyItMatters,
    recommendedAction: c.recommendedAction,
    status: c.status,
    userFeedback: feedbackMap.get(`churn:${c.id}`) ?? null,
    createdAt: c.createdAt.toISOString(),
  }))

  const boardReactivationTargets = validReactivation.map(rv => ({
    id: rv.id,
    contactName: rv.contactName,
    email: rv.email,
    company: rv.company,
    lastContactDate: rv.lastContactDate.toISOString(),
    history: rv.history,
    whyContact: rv.whyContact,
    suggestedOffer: rv.suggestedOffer,
    suggestedMessage: rv.suggestedMessage,
    status: rv.status,
    userFeedback: feedbackMap.get(`reactivation:${rv.id}`) ?? null,
  }))

  const notUsefulIds = new Set(
    feedbackRows.filter(f => f.feedback === 'not_useful').map(f => f.signalId)
  )

  const data: BoardData = {
    isGmailConnected: !!token,
    lastSyncAt: token?.lastSyncAt?.toISOString() ?? null,
    topActions: buildTopActions(boardOpportunities, boardChurnSignals, boardReactivationTargets, 10, notUsefulIds),
    opportunities: boardOpportunities,
    churnSignals: boardChurnSignals,
    retentionInsights: retentionInsights.map(r => ({
      id: r.id,
      clientName: r.clientName,
      insight: r.insight,
      suggestedMessage: r.suggestedMessage,
      timing: r.timing,
      status: r.status,
      createdAt: r.createdAt.toISOString(),
    })),
    reactivationTargets: boardReactivationTargets,
    revenueRecoveredThisMonth: revenueThisMonth > 0 ? formatMoney(revenueThisMonth) : '$0',
    revenueRecoveredAllTime: revenueAllTime > 0 ? formatMoney(revenueAllTime) : '$0',
    accuracyScore,
    syncStats: token
      ? {
          threadsAnalyzed: token.threadsAnalyzed,
          emailsAnalyzed: token.emailsAnalyzed,
          lastSyncError: token.lastSyncError ?? null,
        }
      : null,
    summary: {
      estimatedRevenue: estimatedRevenue > 0 ? `$${estimatedRevenue.toLocaleString()}` : '—',
      opportunityCount: boardOpportunities.length,
      churnCount: boardChurnSignals.length,
      retentionCount: retentionInsights.length,
      reactivationCount: boardReactivationTargets.length,
    },
  }

  return NextResponse.json(data)
}
