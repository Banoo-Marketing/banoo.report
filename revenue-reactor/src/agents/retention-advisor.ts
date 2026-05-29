import { callClaudeJSON } from '@/lib/claude'
import type { EmailThread, RetentionInsightResult } from '@/types'

const SYSTEM = `You are a client success AI. Find retention opportunities in email conversations with existing clients.

Look for: mentioned goals or milestones, promises made, upcoming events, seasonal opportunities, upsell moments, personal context relevant to business, ongoing needs not yet addressed.

Only output insights for existing clients (not new leads). Return null-score if this is a new prospect.

Output ONLY valid JSON:
{
  "clientName": "string",
  "isExistingClient": true,
  "insight": "string (specific retention opportunity from the conversation)",
  "suggestedMessage": "string (2-3 sentence message to send)",
  "timing": "string (e.g. 'This week', 'Before end of month', 'Next Monday')"
}`

interface RawResult {
  clientName: string
  isExistingClient: boolean
  insight: string
  suggestedMessage: string
  timing: string
}

export async function adviseRetention(thread: EmailThread, userEmail: string): Promise<RetentionInsightResult | null> {
  const conversation = thread.messages
    .map(m => `From: ${m.from}\n${m.bodyText.slice(0, 1000)}`)
    .join('\n---\n')

  try {
    const result = await callClaudeJSON<RawResult>(SYSTEM,
      `User email: ${userEmail}\nThread: "${thread.subject}"\n\n${conversation.slice(0, 5000)}`)
    if (!result.isExistingClient) return null
    return {
      clientName: result.clientName,
      insight: result.insight,
      suggestedMessage: result.suggestedMessage,
      timing: result.timing,
    }
  } catch {
    return null
  }
}
