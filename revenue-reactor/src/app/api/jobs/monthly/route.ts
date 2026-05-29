import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/db'
import { callClaudeJSON } from '@/lib/claude'
import type { OutreachContact } from '@/types'

const SYSTEM = `Generate a prioritized monthly outreach list of 20 contacts. Output ONLY a JSON array: [{ "name": "string", "email": "string", "company": "string", "reason": "string", "suggestedMessage": "string", "priority": 1 }]`

export async function GET(req: NextRequest) {
  if (req.headers.get('authorization') !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const month = new Date().toISOString().slice(0, 7)
  const users = await prisma.user.findMany({ select: { id: true, email: true } })
  const results = []

  for (const user of users) {
    try {
      const [opps, reacts] = await Promise.all([
        prisma.opportunity.findMany({ where: { userId: user.id }, orderBy: { opportunityScore: 'desc' }, take: 10 }),
        prisma.reactivationTarget.findMany({ where: { userId: user.id }, orderBy: { lastContactDate: 'asc' }, take: 15 }),
      ])

      const contacts = await callClaudeJSON<OutreachContact[]>(SYSTEM,
        `Month: ${month}\nOpportunities: ${JSON.stringify(opps.map(o => ({ name: o.contactName, company: o.company, score: o.opportunityScore })))}\nReactivations: ${JSON.stringify(reacts.map(r => ({ name: r.contactName, email: r.email, history: r.history })))}`,
        3000)

      await prisma.monthlyOutreachList.upsert({
        where: { userId_month: { userId: user.id, month } },
        update: { contacts: contacts as unknown as Parameters<typeof prisma.monthlyOutreachList.upsert>[0]['update']['contacts'], generatedAt: new Date() },
        create: { userId: user.id, month, contacts: contacts as unknown as Parameters<typeof prisma.monthlyOutreachList.create>[0]['data']['contacts'] },
      })

      results.push({ userId: user.id, status: 'ok' })
    } catch (err) {
      results.push({ userId: user.id, error: String(err) })
    }
  }

  return NextResponse.json({ month, generated: results.length, results })
}
