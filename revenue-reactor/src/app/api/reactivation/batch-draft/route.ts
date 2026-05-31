import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'
import { getAuthClient, createGmailDraft } from '@/lib/gmail'
import { callClaudeJSON } from '@/lib/claude'
import type { ScanContact } from '../scan/route'

const SYSTEM = `You write short reactivation emails for a marketing agency owner.

Rules (non-negotiable):
- Max 80 words in body
- Subject: under 8 words
- No "hope this finds you well", no "touching base", no "circle back"
- Reference the specific past context in 1 sentence
- Ask exactly ONE yes/no question
- Sound like a real person who remembers the conversation
- Sign off as: — Emod

Output ONLY JSON: { "subject": "string", "body": "string" }`

export async function POST(req: Request) {
  const { session, error } = await requireSession()
  if (error) return error

  const { contacts } = await req.json() as { contacts: ScanContact[] }
  if (!contacts?.length) return NextResponse.json({ error: 'No contacts provided' }, { status: 400 })

  const token = await prisma.gmailToken.findUnique({ where: { userId: session.user.id } })
  if (!token) return NextResponse.json({ error: 'Gmail not connected' }, { status: 400 })

  const auth = getAuthClient(token.accessToken, token.refreshToken)
  const results: Array<{ email: string; name: string; subject: string; draftId: string; error?: string }> = []

  for (const contact of contacts.slice(0, 10)) {
    try {
      const draft = await callClaudeJSON<{ subject: string; body: string }>(
        SYSTEM,
        `Contact: ${contact.name} (${contact.email})
Company: ${contact.company || 'unknown'}
Last contact: ${contact.daysSilent} days ago
Context from last thread: "${contact.snippet}"
Reason to re-engage: ${contact.reason}`
      )

      const { draftId } = await createGmailDraft(auth, contact.email, draft.subject, draft.body)

      await prisma.reactivationEmail.create({
        data: {
          userId: session.user.id,
          contactName: contact.name,
          email: contact.email,
          company: contact.company || '',
          subject: draft.subject,
          draftId,
          score: contact.score,
          status: 'drafted',
        },
      })

      results.push({ email: contact.email, name: contact.name, subject: draft.subject, draftId })
    } catch (err) {
      results.push({ email: contact.email, name: contact.name, subject: '', draftId: '', error: String(err) })
    }
  }

  return NextResponse.json({ created: results.filter(r => !r.error), failed: results.filter(r => r.error) })
}
