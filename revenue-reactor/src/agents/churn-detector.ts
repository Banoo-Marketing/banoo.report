import { callClaudeJSON } from '@/lib/claude'
import type { EmailThread, ChurnSignalResult } from '@/types'

const SYSTEM = `You are a client retention AI. Detect churn risk in email conversations.

Signals: complaints, frustration, "not happy", "not working", slow responses, reduced engagement, competitor mentions, cancellation intent, pricing objections, contract questions.

Score 0-100 where:
- 71-100: Urgent — client likely to leave soon
- 41-70: Watch — early warning signs
- 0-40: Safe — no significant risk (return this score to indicate skip)

Output ONLY valid JSON:
{
  "clientName": "string",
  "churnScore": 0,
  "riskLevel": "low|medium|high",
  "reasons": ["string"],
  "recommendedAction": "string (specific retention step)"
}`

export async function detectChurn(thread: EmailThread, userEmail: string): Promise<ChurnSignalResult | null> {
  const conversation = thread.messages
    .map(m => `From: ${m.from}\n${m.bodyText.slice(0, 1500)}`)
    .join('\n---\n')

  try {
    const result = await callClaudeJSON<ChurnSignalResult>(SYSTEM,
      `User email: ${userEmail}\nThread: "${thread.subject}"\n\n${conversation.slice(0, 6000)}`)
    if (result.churnScore < 41) return null
    return result
  } catch {
    return null
  }
}
