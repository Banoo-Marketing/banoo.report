import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/db'
import { generateDailyReport } from '@/agents/daily-report'

export async function GET(req: NextRequest) {
  const secret = req.headers.get('authorization')?.replace('Bearer ', '')
  if (secret !== process.env.CRON_SECRET) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const users = await prisma.user.findMany({ select: { id: true } })
  const reports = []

  for (const user of users) {
    try {
      const report = await generateDailyReport(user.id)
      reports.push({ userId: user.id, report })
    } catch (err) {
      console.error(`Daily report failed for user ${user.id}:`, err)
    }
  }

  return NextResponse.json({ generated: reports.length, reports })
}
