import { callClaudeJSON } from '@/lib/claude'
import type { EmailThread, ChurnResult } from '@/types'

const SYSTEM_PROMPT = `You are a client retention AI that detects churn risk in email conversations.

Churn signals to watch for:
- Client complaints or expressions of frustration
- Reduced email engagement or shorter replies
- Mentions of competitors or alternative solutions
- Requests to cancel, pause, or reduce services
- Questions about contracts or exit clauses
- Expressing dissatisfaction with results or deliverables
- Long gaps in communication from previously active clients
- Budget concerns or cost-cutting language
- "We need to talk" type messages

Output ONLY a JSON object:
{
  "client": "string (name or company)",
  "churn_score": number (0-100, 100 = certain churn),
  "risk_level": "low" | "medium" | "high",
  "reasons": ["string"],
  "recommended_action": "string (specific retention strategy)"
}

If no churn risk, return churn_score: 0.`

export async function detectChurnRisk(
  thread: EmailThread,
  userEmail: string
): Promise<ChurnResult | null> {
  const conversationText = thread.messages
    .map(m => `From: ${m.from}\nDate: ${m.sentAt.toISOString()}\n${m.bodyText.slice(0, 1500)}`)
    .join('\n\n---\n\n')

  const userPrompt = `Analyze this email thread for client churn risk.

User email (business owner/service provider): ${userEmail}
Thread subject: ${thread.subject}
Participants: ${thread.participants.join(', ')}

Conversation:
${conversationText.slice(0, 6000)}`

  try {
    const result = await callClaudeJSON<ChurnResult>(SYSTEM_PROMPT, userPrompt)
    if (result.churn_score < 35) return null
    return result
  } catch {
    return null
  }
}
