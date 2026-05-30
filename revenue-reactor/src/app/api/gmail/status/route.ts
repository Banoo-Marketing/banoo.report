import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'

export async function GET() {
  const { session, error } = await requireSession()
  if (error) return error

  const token = await prisma.gmailToken.findUnique({ where: { userId: session!.user.id } })

  if (!token) {
    return NextResponse.json({
      connected: false,
      lastSyncAt: null,
      threadsAnalyzed: 0,
      emailsAnalyzed: 0,
      lastSyncError: null,
    })
  }

  return NextResponse.json({
    connected: true,
    lastSyncAt: token.lastSyncAt?.toISOString() ?? null,
    threadsAnalyzed: token.threadsAnalyzed,
    emailsAnalyzed: token.emailsAnalyzed,
    lastSyncError: token.lastSyncError ?? null,
  })
}
