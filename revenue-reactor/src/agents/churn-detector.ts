import { callClaudeJSON } from '@/lib/claude'
import type { EmailThread, ChurnSignalResult } from '@/types'

const SYSTEM = `You are a client retention AI. Detect churn risk in email conversations.

STRICT RULE — only flag churn if ALL of the following:
1. The person is an ACTIVE paying client (evidence of ongoing contract, recurring service, or significant past payment implied)
2. AND at least one of: explicit complaint stated directly, two or more separate negative signals, or inactivity 2+ weeks combined with evidence of high-value relationship (implied revenue >$1,000)

DO NOT flag: prospects, cold leads, one-time small purchases, general questions, routine check-ins, minor delays, or anyone who has not paid you money.

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
