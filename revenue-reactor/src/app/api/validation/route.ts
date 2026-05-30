import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'

export async function GET() {
  const { session, error } = await requireSession()
  if (error) return error

  const userId = session!.user.id
  const sixMonthsAgo = new Date(Date.now() - 180 * 24 * 60 * 60 * 1000)

  const [opportunities, churnSignals, reactivationTargets, feedback] = await Promise.all([
    prisma.opportunity.findMany({
      where: { userId, createdAt: { gte: sixMonthsAgo } },
      orderBy: { opportunityScore: 'desc' },
      take: 20,
    }),
    prisma.churnSignal.findMany({
      where: { userId, createdAt: { gte: sixMonthsAgo } },
      orderBy: { churnScore: 'desc' },
      take: 10,
    }),
    prisma.reactivationTarget.findMany({
      where: { userId, createdAt: { gte: sixMonthsAgo } },
      orderBy: { lastContactDate: 'asc' },
      take: 20,
    }),
    prisma.signalFeedback.findMany({ where: { userId } }),
  ])

  const feedbackByKey = new Map(feedback.map(f => [`${f.signalType}:${f.signalId}`, f.feedback]))

  const exportData = {
    generatedAt: new Date().toISOString(),
    period: { from: sixMonthsAgo.toISOString(), to: new Date().toISOString() },
    top20Opportunities: opportunities.map(o => ({
      name: o.contactName,
      company: o.company,
      score: o.opportunityScore,
      confidence: o.revenueConfidence,
      value: o.estimatedValue,
      reason: o.reason,
      evidence: o.evidence,
      action: o.suggestedAction,
      status: o.status,
      feedback: feedbackByKey.get(`opportunity:${o.id}`) ?? null,
      foundAt: o.createdAt.toISOString(),
    })),
    top10ChurnRisks: churnSignals.map(c => ({
      client: c.clientName,
      score: c.churnScore,
      risk: c.riskLevel,
      whatHappened: c.whatHappened,
      action: c.recommendedAction,
      status: c.status,
      feedback: feedbackByKey.get(`churn:${c.id}`) ?? null,
      foundAt: c.createdAt.toISOString(),
    })),
    top20Reactivations: reactivationTargets.map(rv => ({
      name: rv.contactName,
      company: rv.company,
      email: rv.email,
      whyNow: rv.whyContact,
      offer: rv.suggestedOffer,
      lastContact: rv.lastContactDate.toISOString(),
      status: rv.status,
      feedback: feedbackByKey.get(`reactivation:${rv.id}`) ?? null,
    })),
  }

  return NextResponse.json(exportData)
}
