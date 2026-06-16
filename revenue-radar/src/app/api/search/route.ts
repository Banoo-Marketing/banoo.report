import { NextRequest, NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'

export async function GET(req: NextRequest) {
  const { session, error } = await requireSession()
  if (error) return error

  const userId = session!.user!.id!
  const query = req.nextUrl.searchParams.get('q') ?? ''

  if (!query.trim()) {
    return NextResponse.json({ data: { opportunities: [], churn: [], reactivations: [] } })
  }

  const [opportunities, churn, reactivations] = await Promise.all([
    prisma.opportunitySignal.findMany({
      where: {
        userId,
        OR: [
          { contactName: { contains: query, mode: 'insensitive' } },
          { company: { contains: query, mode: 'insensitive' } },
          { reason: { contains: query, mode: 'insensitive' } },
          { recommendedAction: { contains: query, mode: 'insensitive' } },
        ],
      },
      take: 10,
    }),
    prisma.churnSignal.findMany({
      where: {
        userId,
        OR: [
          { client: { contains: query, mode: 'insensitive' } },
          { recommendedAction: { contains: query, mode: 'insensitive' } },
        ],
      },
      take: 10,
    }),
    prisma.reactivationContact.findMany({
      where: {
        userId,
        OR: [
          { name: { contains: query, mode: 'insensitive' } },
          { company: { contains: query, mode: 'insensitive' } },
          { email: { contains: query, mode: 'insensitive' } },
          { reactivationReason: { contains: query, mode: 'insensitive' } },
        ],
      },
      take: 10,
    }),
  ])

  return NextResponse.json({ data: { opportunities, churn, reactivations } })
}
