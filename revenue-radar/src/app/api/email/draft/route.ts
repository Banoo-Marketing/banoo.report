import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'
import { callClaudeJSON } from '@/lib/claude'
import type { EmailDraftRequest, GeneratedEmailDraft } from '@/types'

const DRAFT_SYSTEM_PROMPT = `You are an expert email copywriter. Generate professional, concise business emails.

Rules:
- Subject line: clear and specific, under 60 characters
- Body: 3-5 sentences max, professional tone
- Always include a clear CTA
- Match the specified tone
- No generic filler phrases

Output ONLY JSON:
{
  "subject": "string",
  "body": "string",
  "tone": "string"
}`

export async function POST(req: Request) {
  const { session, error } = await requireSession()
  if (error) return error

  const userId = session!.user!.id!
  const body = await req.json() as EmailDraftRequest

  const userPrompt = `Generate a ${body.tone ?? 'professional'} email for the following context:

Signal type: ${body.signalType}
Recipient: ${body.to}
Context: ${body.context}

The email should be appropriate for the signal type:
- opportunity: Express interest and propose next steps
- followup: Politely check in on a previous conversation
- churn: Address concerns and offer solutions to retain the client
- reactivation: Friendly check-in to reconnect and offer value`

  try {
    const draft = await callClaudeJSON<GeneratedEmailDraft>(DRAFT_SYSTEM_PROMPT, userPrompt)

    const saved = await prisma.emailDraft.create({
      data: {
        userId,
        threadId: body.threadId ?? null,
        to: body.to,
        subject: draft.subject,
        body: draft.body,
        tone: draft.tone ?? body.tone ?? 'professional',
        status: 'DRAFT',
      },
    })

    return NextResponse.json({ data: saved })
  } catch (err) {
    console.error('Draft generation error:', err)
    return NextResponse.json({ error: 'Failed to generate draft' }, { status: 500 })
  }
}
