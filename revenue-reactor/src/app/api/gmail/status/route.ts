import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'

export async function GET() {
  const { session, error } = await requireSession()
  if (error) return error

  const token = await prisma.gmailToken.findUnique({ where: { userId: session!.user.id } })
  return NextResponse.json({ connected: !!token, lastSyncAt: token?.lastSyncAt ?? null })
}
