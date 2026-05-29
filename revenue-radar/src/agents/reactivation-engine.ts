import { callClaudeJSON } from '@/lib/claude'
import type { EmailThread, ReactivationResult } from '@/types'

const SYSTEM_PROMPT = `You are a client reactivation AI. You analyze old email conversations to identify past clients or prospects worth reaching out to again.

Reactivation opportunities:
- Past clients who haven't been in touch for 30+ days
- Leads that went cold without a clear "no"
- Clients whose project ended but could have new needs
- Prospects who showed interest but never converted
- Former clients who left on good terms

Generate a personalized outreach strategy.

Output ONLY a JSON object:
{
  "contact": "string (full name)",
  "email": "string",
  "company": "string",
  "last_contact_date": "ISO date string",
  "reactivation_reason": "string (why this person is worth re-engaging)",
  "recommended_offer": "string (specific offer or value proposition)",
  "email_draft": "string (full email body, 3-5 sentences, personalized and non-pushy)"
}`

export async function generateReactivation(
  thread: EmailThread,
  userEmail: string,
  minDaysInactive = 30
): Promise<ReactivationResult | null> {
  const now = new Date()
  const daysSinceLastActivity = Math.floor(
    (now.getTime() - thread.lastMessageAt.getTime()) / (1000 * 60 * 60 * 24)
  )

  if (daysSinceLastActivity < minDaysInactive) return null

  const conversationText = thread.messages
    .map(m => `From: ${m.from}\nDate: ${m.sentAt.toISOString()}\n${m.bodyText.slice(0, 1000)}`)
    .join('\n\n---\n\n')

  const userPrompt = `Analyze this old email thread and generate a reactivation strategy.

User email (business owner): ${userEmail}
Thread subject: ${thread.subject}
Last activity: ${thread.lastMessageAt.toISOString()} (${daysSinceLastActivity} days ago)
Participants: ${thread.participants.join(', ')}

Conversation history:
${conversationText.slice(0, 5000)}`

  try {
    const result = await callClaudeJSON<ReactivationResult>(SYSTEM_PROMPT, userPrompt)
    if (!result.email) {
      const otherParticipant = thread.participants.find(p => !p.includes(userEmail))
      result.email = otherParticipant ? otherParticipant.match(/<([^>]+)>/)?.[1] ?? otherParticipant : ''
    }
    result.last_contact_date = thread.lastMessageAt.toISOString()
    return result
  } catch {
    return null
  }
}
