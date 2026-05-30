import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'
import type { SignalKind } from '@/types'

export async function PATCH(req: Request) {
  const { session, error } = await requireSession()
  if (error) return error

  const userId = session!.user.id
  const { signalId, signalType, status } = await req.json() as {
    signalId: string
    signalType: SignalKind
    status: string
  }

  if (signalType === 'opportunity') {
    await prisma.opportunity.updateMany({ where: { id: signalId, userId }, data: { status } })
  } else if (signalType === 'churn') {
    await prisma.churnSignal.updateMany({ where: { id: signalId, userId }, data: { status } })
  } else if (signalType === 'reactivation') {
    await prisma.reactivationTarget.updateMany({ where: { id: signalId, userId }, data: { status } })
  }

  return NextResponse.json({ ok: true })
}
