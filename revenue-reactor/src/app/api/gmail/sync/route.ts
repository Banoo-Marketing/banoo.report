import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { syncUser } from '@/lib/sync'

export async function POST() {
  const { session, error } = await requireSession()
  if (error) return error

  try {
    const result = await syncUser(session!.user.id, session!.user.email!)
    return NextResponse.json({ success: true, ...result })
  } catch (err) {
    console.error('Sync error:', err)
    return NextResponse.json({ error: 'Sync failed' }, { status: 500 })
  }
}
