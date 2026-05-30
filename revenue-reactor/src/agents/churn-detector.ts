import { callClaudeJSON } from '@/lib/claude'
import type { EmailThread, ChurnSignalResult } from '@/types'

const SYSTEM = `You are a client retention AI. Detect churn risk in email conversations.

STRICT RULE — only flag churn if at least one of these is true:
1. Explicit complaint or dissatisfaction stated directly in the email
2. Two or more separate negative signals in the conversation (slow response + complaint, price objection + competitor mention, etc.)
3. Significant inactivity (2+ weeks no response) combined with evidence the client was previously high-value

DO NOT flag: general questions, routine check-ins, minor delays, or single neutral comments.

Score 0-100:
- 71-100: Act today — client is likely to leave
- 41-70: Watch — meaningful warning signs present
- 0-40: Not churn risk — return churnScore: 0

whatHappened: Describe exactly what the client said or did. Quote them if possible. 2-3 sentences.
whyItMatters: The specific business impact if they leave. Be concrete (revenue figure if known). 1-2 sentences.
recommendedAction: Use imperative language. "Call [Client] today", "Send value recap today", "Schedule a call this week".
Never use: "consider", "you may want to", "might", "could", "possibly".

Output ONLY valid JSON:
{
  "clientName": "string",
  "churnScore": 0,
  "riskLevel": "low|medium|high",
  "reasons": ["string — specific signal from the conversation"],
  "whatHappened": "string",
  "whyItMatters": "string",
  "recommendedAction": "string (imperative)"
}`

export async function detectChurn(thread: EmailThread, userEmail: string): Promise<ChurnSignalResult | null> {
  const conversation = thread.messages
    .map(m => `From: ${m.from}\n${m.bodyText.slice(0, 1500)}`)
    .join('\n---\n')

  try {
    const result = await callClaudeJSON<ChurnSignalResult>(SYSTEM,
      `User email: ${userEmail}\nThread: "${thread.subject}"\n\n${conversation.slice(0, 6000)}`)
    if (result.churnScore < 55) return null
    return result
  } catch {
    return null
  }
}
