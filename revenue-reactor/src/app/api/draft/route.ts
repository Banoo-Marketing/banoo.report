import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { callClaudeJSON } from '@/lib/claude'

const SYSTEM = `You are an expert email copywriter. Write a short, professional business email.
Rules: Subject under 60 chars. Body 3-5 sentences. Include a clear CTA. Natural, human tone.
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
