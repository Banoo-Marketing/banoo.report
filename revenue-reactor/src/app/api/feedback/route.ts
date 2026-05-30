import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'
import type { FeedbackValue, SignalKind } from '@/types'

export async function POST(req: Request) {
  const { session, error } = await requireSession()
  if (error) return error

  const userId = session!.user.id
  const { signalId, signalType, feedback } = await req.json() as {
    signalId: string
    signalType: SignalKind
    feedback: FeedbackValue
  }

  await prisma.signalFeedback.upsert({
    where: { userId_signalType_signalId: { userId, signalType, signalId } },
    update: { feedback },
    create: { userId, signalType, signalId, feedback },
  })

  return NextResponse.json({ ok: true })
}
