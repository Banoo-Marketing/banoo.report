import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'
import type { DashboardMetrics } from '@/types'

export async function GET() {
  const { session, error } = await requireSession()
  if (error) return error

  const userId = session!.user!.id!

  const [gmailToken, opportunities, churnSignals, reactivations, followUps] = await Promise.all([
    prisma.gmailToken.findUnique({ where: { userId } }),
    prisma.opportunitySignal.count({ where: { userId, status: 'new' } }),
    prisma.churnSignal.count({ where: { userId, status: 'new' } }),
    prisma.reactivationContact.count({ where: { userId, status: 'pending' } }),
    prisma.emailThread.count({
      where: {
        userId,
        isHumanConversation: true,
        lastMessageAt: { lt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) },
        isProcessed: true,
      },
    }),
  ])

  const topOpportunities = await prisma.opportunitySignal.findMany({
    where: { userId, status: 'new', estimatedValue: { not: null } },
    select: { estimatedValue: true },
    take: 20,
  })

  let estimatedRevenue = 0
  for (const op of topOpportunities) {
    const match = op.estimatedValue?.match(/\$?([\d,]+)/)
    if (match) {
      estimatedRevenue += parseInt(match[1].replace(',', ''), 10)
    }
  }

  const metrics: DashboardMetrics = {
    totalOpportunities: opportunities,
    estimatedRevenue: estimatedRevenue > 0 ? `$${estimatedRevenue.toLocaleString()}` : 'Unknown',
    followUpsNeeded: followUps,
    churnRisks: churnSignals,
    reactivationTargets: reactivations,
    lastSyncAt: gmailToken?.lastSyncAt ?? null,
    isGmailConnected: !!gmailToken,
  }

  return NextResponse.json({ data: metrics })
}
