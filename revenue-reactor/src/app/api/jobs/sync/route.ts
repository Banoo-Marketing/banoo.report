import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/db'
import { syncUser } from '@/lib/sync'

export async function GET(req: NextRequest) {
  if (req.headers.get('authorization') !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const users = await prisma.user.findMany({ include: { gmailToken: true }, where: { gmailToken: { isNot: null } } })
  const results = []

  for (const user of users) {
    try {
      const r = await syncUser(user.id, user.email)
      results.push({ userId: user.id, ...r })
    } catch (err) {
      results.push({ userId: user.id, error: String(err) })
    }
  }

  return NextResponse.json({ synced: results.length, results })
}
