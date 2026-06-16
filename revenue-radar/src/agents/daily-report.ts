import { callClaudeJSON } from '@/lib/claude'
import type { DailyReportResult } from '@/types'
import { prisma } from '@/lib/db'

const SYSTEM_PROMPT = `You are a revenue intelligence analyst. Generate a concise, actionable daily revenue report.
Focus only on what matters. No fluff. Prioritize actions that recover or protect revenue.

Output ONLY a JSON object:
{
  "date": "ISO date string",
  "new_opportunities": number,
  "follow_ups_needed": number,
  "churn_risks": number,
  "reactivation_targets": number,
  "estimated_revenue_at_risk": "string",
  "top_actions": ["string (3 specific actions)"],
  "summary": "string (2-3 sentence executive summary)"
}`

export async function generateDailyReport(userId: string): Promise<DailyReportResult> {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const [opportunities, churnSignals, reactivations, followUps] = await Promise.all([
    prisma.opportunitySignal.findMany({
      where: { userId, status: 'new' },
      orderBy: { opportunityScore: 'desc' },
      take: 10,
    }),
    prisma.churnSignal.findMany({
      where: { userId, status: 'new' },
      orderBy: { churnScore: 'desc' },
      take: 10,
    }),
    prisma.reactivationContact.findMany({
      where: { userId, status: 'pending' },
      orderBy: { lastContactDate: 'asc' },
      take: 10,
    }),
    prisma.emailThread.findMany({
      where: {
        userId,
        isHumanConversation: true,
        lastMessageAt: { lt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) },
      },
      take: 10,
    }),
  ])

  const dataContext = JSON.stringify(
    {
      opportunities: opportunities.map(o => ({
        contact: o.contactName,
        score: o.opportunityScore,
        value: o.estimatedValue,
        reason: o.reason,
      })),
      churn_risks: churnSignals.map(c => ({
        client: c.client,
        score: c.churnScore,
        risk: c.riskLevel,
        reasons: c.reasons,
      })),
      reactivations: reactivations.map(r => ({
        contact: r.name,
        days_inactive: Math.floor((Date.now() - r.lastContactDate.getTime()) / 86400000),
        offer: r.recommendedOffer,
      })),
      stalled_threads: followUps.length,
    },
    null,
    2
  )

  const userPrompt = `Generate a daily revenue report for today (${new Date().toDateString()}).

Current pipeline data:
${dataContext}`

  try {
    const result = await callClaudeJSON<DailyReportResult>(SYSTEM_PROMPT, userPrompt, { maxTokens: 1024 })
    result.date = new Date().toISOString()
    result.new_opportunities = opportunities.length
    result.follow_ups_needed = followUps.length
    result.churn_risks = churnSignals.length
    result.reactivation_targets = reactivations.length
    return result
  } catch {
    return {
      date: new Date().toISOString(),
      new_opportunities: opportunities.length,
      follow_ups_needed: followUps.length,
      churn_risks: churnSignals.length,
      reactivation_targets: reactivations.length,
      estimated_revenue_at_risk: 'Unknown',
      top_actions: [
        'Review and respond to top opportunities',
        'Send follow-ups to stalled conversations',
        'Address at-risk client concerns',
      ],
      summary: `You have ${opportunities.length} new opportunities and ${churnSignals.length} clients at risk. Take action on your top 3 priorities today.`,
    }
  }
}
