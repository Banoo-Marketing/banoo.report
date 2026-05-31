import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'

export async function GET() {
  const { session, error } = await requireSession()
  if (error) return error

  const emails = await prisma.reactivationEmail.findMany({
    where: { userId: session.user.id, status: { in: ['drafted', 'sent'] } },
    orderBy: { sentAt: 'desc' },
    take: 50,
  })

  const now = Date.now()

  const enriched = emails.map(e => {
    const daysSince = Math.floor((now - e.sentAt.getTime()) / 86400000)
    const needsDay3 = daysSince >= 3 && !e.followUp3
    const needsDay7 = daysSince >= 7 && !e.followUp7
    const needsDay14 = daysSince >= 14 && !e.followUp14

    return {
      id: e.id,
      contactName: e.contactName,
      email: e.email,
      company: e.company,
      subject: e.subject,
      draftId: e.draftId,
      sentAt: e.sentAt.toISOString(),
      daysSince,
      status: e.status,
      score: e.score,
      followUp: needsDay14 ? 'day14' : needsDay7 ? 'day7' : needsDay3 ? 'day3' : null,
    }
  })

  return NextResponse.json({
    all: enriched,
    needsFollowUp: enriched.filter(e => e.followUp !== null),
  })
}

export async function PATCH(req: Request) {
  const { session, error } = await requireSession()
  if (error) return error

  const { id, followUpDay, status } = await req.json() as {
    id: string
    followUpDay?: 3 | 7 | 14
    status?: string
  }

  const data: Record<string, unknown> = {}
  if (followUpDay === 3) data.followUp3 = true
  if (followUpDay === 7) data.followUp7 = true
  if (followUpDay === 14) data.followUp14 = true
  if (status) data.status = status

  const updated = await prisma.reactivationEmail.update({ where: { id }, data })
  return NextResponse.json(updated)
}
