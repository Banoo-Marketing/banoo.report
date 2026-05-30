import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { callClaudeJSON } from '@/lib/claude'

const SYSTEM = `You are a business owner writing a direct personal email.

Structure (follow exactly):
- Sentence 1: one sentence of context referencing the specific situation
- Middle: one clear ask or offer (what you want from this email)
- Final line: one question that invites a response (the CTA)

Hard rules:
- Body: 120 words maximum. Count carefully.
- Subject: under 50 characters
- Sound like a real person — direct, warm, no filler
- Never use: "I hope this finds you well", "touch base", "circle back", "synergy", "leverage", "reach out", "following up to follow up"

Output ONLY JSON: { "subject": "string", "body": "string" }`

export async function POST(req: Request) {
  const { session, error } = await requireSession()
  if (error) return error

  const { type, to, context, prompt } = await req.json() as { type: string; to: string; context: string; prompt: string }

  try {
    const draft = await callClaudeJSON<{ subject: string; body: string }>(
      SYSTEM,
      `Email type: ${type}\nRecipient: ${to}\nContext: ${context}\nInstruction: ${prompt}`
    )
    return NextResponse.json(draft)
  } catch (err) {
    console.error('Draft error:', err)
    return NextResponse.json({ error: 'Draft failed' }, { status: 500 })
  }
}
