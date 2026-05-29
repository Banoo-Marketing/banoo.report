import { callClaudeJSON } from '@/lib/claude'
import type { EmailThread, MissedFollowupResult } from '@/types'

const SYSTEM_PROMPT = `You are a follow-up intelligence AI. You analyze email threads to identify conversations where a business owner needs to send a follow-up but hasn't.

Signs that follow-up is needed:
- The business owner sent a proposal/quote but got no response
- A prospect asked questions that were answered but never replied back
- A conversation was progressing toward a sale and then went cold
- A client hasn't responded to an important message
- A meeting or call was discussed but never confirmed

Output ONLY a JSON object:
{
  "thread_id": "string",
  "contact_name": "string",
  "last_activity": "ISO date string",
  "days_inactive": number,
  "estimated_value": "string",
  "follow_up_needed": boolean,
  "recommended_email_draft": "string (2-3 sentence follow-up email body)"
}`

export async function detectMissedFollowup(
  thread: EmailThread,
  userEmail: string,
  daysThreshold = 7
): Promise<MissedFollowupResult | null> {
  const now = new Date()
  const daysSinceLastActivity = Math.floor(
    (now.getTime() - thread.lastMessageAt.getTime()) / (1000 * 60 * 60 * 24)
  )

  if (daysSinceLastActivity < daysThreshold) return null

  const conversationText = thread.messages
    .map(m => `From: ${m.from}\nDate: ${m.sentAt.toISOString()}\n${m.bodyText.slice(0, 1500)}`)
    .join('\n\n---\n\n')

  const userPrompt = `Analyze if a follow-up email is needed for this thread.

User email (business owner): ${userEmail}
Thread subject: ${thread.subject}
Last activity: ${thread.lastMessageAt.toISOString()}
Days since last message: ${daysSinceLastActivity}

Conversation:
${conversationText.slice(0, 6000)}`

  try {
    const result = await callClaudeJSON<MissedFollowupResult>(SYSTEM_PROMPT, userPrompt)
    result.thread_id = thread.gmailThreadId
    result.days_inactive = daysSinceLastActivity
    result.last_activity = thread.lastMessageAt.toISOString()

    if (!result.follow_up_needed) return null
    return result
  } catch {
    return null
  }
}
