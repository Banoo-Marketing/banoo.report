import { callClaudeJSON } from '@/lib/claude'
import type { EmailThread, ReactivationResult } from '@/types'

const SYSTEM = `You are a reactivation AI. Analyze old email threads to find contacts worth re-engaging.

Look for: past clients, inactive leads, old proposals, paused projects, cold conversations that ended without a "no".

Analyze the previous relationship and consider:
- Previous services or products discussed
- Seasonal opportunities (is this person's business seasonal?)
- Business goals they mentioned
- What changed since last contact that makes now a good time to reach out

Generate a personalized, non-pushy reactivation message that references the previous conversation naturally and gives a clear reason WHY now is a good time to reconnect.

Output ONLY valid JSON:
{
  "contactName": "string",
  "email": "string",
  "company": "string",
  "lastContactDate": "ISO date string",
  "history": "string (1-2 sentences about previous relationship)",
  "whyContact": "string (2-3 sentences: why this person specifically, why now, what seasonal or business reason makes this timely)",
  "suggestedOffer": "string (specific value proposition to re-engage)",
  "suggestedMessage": "string (3-4 sentence friendly, human outreach message with clear CTA)"
}`

export async function findReactivation(thread: EmailThread, userEmail: string, minDays = 30): Promise<ReactivationResult | null> {
  const daysSince = Math.floor((Date.now() - thread.lastMessageAt.getTime()) / 86400000)
  if (daysSince < minDays) return null

  const otherParticipant = thread.participants.find(p => !p.toLowerCase().includes(userEmail.split('@')[0]))
  const emailMatch = otherParticipant?.match(/<([^>]+)>/)
  const contactEmail = emailMatch ? emailMatch[1] : (otherParticipant ?? '')

  const conversation = thread.messages
    .map(m => `From: ${m.from}\nDate: ${m.sentAt.toISOString()}\n${m.bodyText.slice(0, 800)}`)
    .join('\n---\n')

  const currentMonth = new Date().toLocaleString('en-US', { month: 'long' })

  try {
    const result = await callClaudeJSON<ReactivationResult>(SYSTEM,
      `User email: ${userEmail}\nThread: "${thread.subject}"\nDays inactive: ${daysSince}\nCurrent month: ${currentMonth}\nKnown contact email: ${contactEmail}\n\n${conversation.slice(0, 4000)}`)
    if (!result.email) result.email = contactEmail
    result.lastContactDate = thread.lastMessageAt.toISOString()
    return result
  } catch {
    return null
  }
}
