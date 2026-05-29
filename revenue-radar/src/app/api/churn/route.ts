import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'

export async function GET() {
  const { session, error } = await requireSession()
  if (error) return error

  const userId = session!.user!.id!

  const signals = await prisma.churnSignal.findMany({
    where: { userId },
    orderBy: { churnScore: 'desc' },
    take: 50,
    include: { thread: { select: { gmailThreadId: true, subject: true } } },
  })

  return NextResponse.json({ data: signals })
}

export async function PATCH(req: Request) {
  const { session, error } = await requireSession()
  if (error) return error

  const userId = session!.user!.id!
  const { id, status } = await req.json() as { id: string; status: string }

  const updated = await prisma.churnSignal.updateMany({
    where: { id, userId },
    data: { status },
  })

  if (updated.count === 0) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 })
  }

  return NextResponse.json({ success: true })
}
