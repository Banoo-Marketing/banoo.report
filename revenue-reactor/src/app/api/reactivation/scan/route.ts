import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'
import { getAuthClient, searchThreadIds, getThread } from '@/lib/gmail'

export interface ScanContact {
  name: string
  email: string
  company: string
  lastContactDate: string
  daysSilent: number
  score: number
  intentLevel: 'high' | 'medium' | 'low'
  estimatedValue: string
  reason: string
  snippet: string
  threadId: string
}

const QUERIES = [
  'subject:(proposal OR quote OR retainer OR contract OR pricing) -category:promotions',
  '"let me know" OR "interested" OR "send me" OR "can you" OR "follow up" -category:promotions -from:noreply -from:no-reply',
  'subject:(meeting OR call OR schedule) -category:promotions -from:calendar-notification',
]

const HIGH_INTENT = ['proposal', 'quote', 'retainer', 'contract', 'invoice', 'payment', 'pricing', 'budget']
const MED_INTENT = ['meeting', 'call', 'schedule', 'book', 'interested', 'let me know', 'follow up']
const HIGH_VALUE = ['ads', 'advertising', 'marketing', 'seo', 'sem', 'retainer', 'campaign', 'monthly']

function extractEmail(raw: string): string {
  const m = raw.match(/<([^>]+)>/)
  return m ? m[1] : raw.trim()
}

function extractName(raw: string): string {
  const m = raw.match(/^([^<]+)</)
  return m ? m[1].trim().replace(/"/g, '') : raw.split('@')[0]
}

function score(thread: { subject: string; snippet: string; daysSilent: number }): {
  score: number
  intentLevel: 'high' | 'medium' | 'low'
  estimatedValue: string
  reason: string
} {
  const text = `${thread.subject} ${thread.snippet}`.toLowerCase()

  const isHighIntent = HIGH_INTENT.some(k => text.includes(k))
  const isMedIntent = MED_INTENT.some(k => text.includes(k))
  const isHighValue = HIGH_VALUE.some(k => text.includes(k))

  const intent = isHighIntent ? 40 : isMedIntent ? 25 : 10

  const recency =
    thread.daysSilent < 14 ? 30 :
    thread.daysSilent < 30 ? 25 :
    thread.daysSilent < 90 ? 18 :
    thread.daysSilent < 180 ? 12 : 6

  const value = isHighValue ? 20 : 12

  const stagnation =
    thread.daysSilent > 90 ? 10 :
    thread.daysSilent > 30 ? 7 :
    thread.daysSilent > 14 ? 4 : 0

  const total = intent + recency + value + stagnation

  const intentLevel: 'high' | 'medium' | 'low' = isHighIntent ? 'high' : isMedIntent ? 'medium' : 'low'
  const estimatedValue = isHighValue ? '$2K–$8K/mo' : isHighIntent ? '$1K–$5K/mo' : '$500–$2K/mo'

  const reason =
    thread.daysSilent > 90 ? `No reply in ${thread.daysSilent} days — high stagnation` :
    isHighIntent ? 'Active revenue conversation — went quiet' :
    isMedIntent ? 'Meeting or follow-up dropped' :
    'Warm contact — last touched recently'

  return { score: total, intentLevel, estimatedValue, reason }
}

export async function GET() {
  const { session, error } = await requireSession()
  if (error) return error

  const token = await prisma.gmailToken.findUnique({ where: { userId: session.user.id } })
  if (!token) return NextResponse.json({ error: 'Gmail not connected' }, { status: 400 })

  const auth = getAuthClient(token.accessToken, token.refreshToken)
  const userEmail = session.user.email ?? ''

  const seenThreadIds = new Set<string>()
  const contactMap = new Map<string, ScanContact>()

  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - 730) // 2 years back

  for (const q of QUERIES) {
    try {
      const ids = await searchThreadIds(auth, q + ' after:2023/01/01', 60)
      for (const id of ids) {
        if (seenThreadIds.has(id)) continue
        seenThreadIds.add(id)

        const thread = await getThread(auth, id)
        if (!thread) continue

        const { lastMessageAt, participants, subject, snippet } = thread

        if (lastMessageAt < cutoff) continue

        const daysSilent = Math.floor((Date.now() - lastMessageAt.getTime()) / 86400000)
        if (daysSilent < 14) continue // skip active conversations

        const external = participants.find(p => {
          const e = extractEmail(p).toLowerCase()
          return !e.includes(userEmail.split('@')[0]) && !e.includes('noreply') && !e.includes('no-reply')
        })
        if (!external) continue

        const email = extractEmail(external)
        if (!email.includes('@')) continue

        const scored = score({ subject, snippet, daysSilent })
        if (scored.score < 30) continue

        const existing = contactMap.get(email)
        if (!existing || scored.score > existing.score) {
          contactMap.set(email, {
            name: extractName(external),
            email,
            company: '',
            lastContactDate: lastMessageAt.toISOString(),
            daysSilent,
            score: scored.score,
            intentLevel: scored.intentLevel,
            estimatedValue: scored.estimatedValue,
            reason: scored.reason,
            snippet: snippet.slice(0, 120),
            threadId: id,
          })
        }
      }
    } catch {
      // skip failed query
    }
  }

  const ranked = Array.from(contactMap.values())
    .sort((a, b) => b.score - a.score)
    .slice(0, 10)

  return NextResponse.json({ contacts: ranked, scannedThreads: seenThreadIds.size })
}
