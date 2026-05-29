import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'
import { callClaudeJSON } from '@/lib/claude'
import type { OutreachContact } from '@/types'

const SYSTEM = `You are a sales outreach AI. Generate a prioritized list of 20 contacts to re-engage this month.

For each contact, write a short personalized message referencing their specific history.

Output ONLY a JSON array of 20 objects:
[{
  "name": "string",
  "email": "string",
  "company": "string",
  "reason": "string (why this person, this month)",
  "suggestedMessage": "string (2-3 sentence outreach message)",
  "priority": 1
}]

Priority: 1 = highest (send first), 20 = lowest.`

export async function GET() {
  const { session, error } = await requireSession()
  if (error) return error

  const userId = session!.user.id
  const month = new Date().toISOString().slice(0, 7)

  const list = await prisma.monthlyOutreachList.findUnique({ where: { userId_month: { userId, month } } })
  return NextResponse.json({ data: list ?? null, month })
}

export async function POST() {
  const { session, error } = await requireSession()
  if (error) return error

  const userId = session!.user.id
  const month = new Date().toISOString().slice(0, 7)

  const [opportunities, reactivations, churnSignals] = await Promise.all([
    prisma.opportunity.findMany({ where: { userId }, orderBy: { opportunityScore: 'desc' }, take: 15 }),
    prisma.reactivationTarget.findMany({ where: { userId }, orderBy: { lastContactDate: 'asc' }, take: 20 }),
    prisma.churnSignal.findMany({ where: { userId }, orderBy: { churnScore: 'desc' }, take: 5 }),
  ])

  const contextData = {
    opportunities: opportunities.map(o => ({ name: o.contactName, company: o.company, score: o.opportunityScore, value: o.estimatedValue, reason: o.reason })),
    reactivations: reactivations.map(r => ({ name: r.contactName, email: r.email, company: r.company, lastContact: r.lastContactDate.toISOString().slice(0, 10), history: r.history, offer: r.suggestedOffer })),
    atRisk: churnSignals.map(c => ({ name: c.clientName, score: c.churnScore, risk: c.riskLevel })),
  }

  try {
    const contacts = await callClaudeJSON<OutreachContact[]>(SYSTEM,
      `Generate a monthly outreach list for ${month}.\n\nPipeline data:\n${JSON.stringify(contextData, null, 2)}`,
      3000)

    const list = await prisma.monthlyOutreachList.upsert({
      where: { userId_month: { userId, month } },
      update: { contacts: contacts as unknown as Parameters<typeof prisma.monthlyOutreachList.upsert>[0]['update']['contacts'], generatedAt: new Date() },
      create: { userId, month, contacts: contacts as unknown as Parameters<typeof prisma.monthlyOutreachList.create>[0]['data']['contacts'] },
    })

    return NextResponse.json({ data: list, month })
  } catch (err) {
    console.error('Outreach generation error:', err)
    return NextResponse.json({ error: 'Failed to generate outreach list' }, { status: 500 })
  }
}
