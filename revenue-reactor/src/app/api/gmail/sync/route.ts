import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { syncUser, interpretSyncError } from '@/lib/sync'
import { prisma } from '@/lib/db'

export async function POST() {
  const { session, error } = await requireSession()
  if (error) return error

  const userId = session!.user.id

  try {
    const result = await syncUser(userId, session!.user.email!)
    return NextResponse.json({ success: true, ...result })
  } catch (err) {
    console.error('Sync error:', err)
    const message = interpretSyncError(err)
    await prisma.gmailToken.updateMany({ where: { userId }, data: { lastSyncError: message } })
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
