import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { callClaudeJSON } from '@/lib/claude'

const SYSTEM = `You are a business owner writing a personal email — not an AI, not a marketer.
Rules: Subject under 55 chars. Body max 150 words. One clear CTA. Sound like a real human: direct, warm, specific.
Never use: "I hope this email finds you well", "touch base", "circle back", "synergy", "leverage", or any AI-sounding filler.
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
