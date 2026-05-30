import { callClaudeJSON } from '@/lib/claude'
import type { EmailThread, ChurnSignalResult } from '@/types'

const SYSTEM = `You are a client retention AI. Detect churn risk in email conversations.

Signals: complaints, frustration, "not happy", "not working", slow responses, reduced engagement, competitor mentions, cancellation intent, pricing objections, contract questions.

Score 0-100 where:
- 71-100: Urgent — client likely to leave soon
- 41-70: Watch — early warning signs
- 0-40: Safe — no significant risk (skip)

Output ONLY valid JSON:
{
  "clientName": "string",
  "churnScore": 0,
  "riskLevel": "low|medium|high",
  "reasons": ["string"],
  "whatHappened": "string (2-3 sentences describing exactly what the client said or did that raised this flag)",
  "whyItMatters": "string (1-2 sentences explaining the business impact if this client leaves)",
  "recommendedAction": "string (specific, actionable retention step)"
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
