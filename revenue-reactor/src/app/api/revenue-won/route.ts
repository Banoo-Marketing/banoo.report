import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'

export async function PATCH(req: Request) {
  const { session, error } = await requireSession()
  if (error) return error

  const userId = session!.user.id
  const { opportunityId, amount } = await req.json() as { opportunityId: string; amount: number }

  if (!opportunityId || typeof amount !== 'number' || amount < 0) {
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 })
  }

  await prisma.opportunity.updateMany({
    where: { id: opportunityId, userId },
    data: { status: 'won', revenueRecovered: amount, revenueWonAt: new Date() },
  })

  return NextResponse.json({ ok: true })
}
