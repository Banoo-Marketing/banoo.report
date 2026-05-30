import { callClaudeJSON } from '@/lib/claude'
import type { EmailThread, ReactivationResult } from '@/types'

const SYSTEM = `You are a reactivation AI. Analyze old email threads to find contacts worth re-engaging.

STRICT RULE — only flag for reactivation if at least one of these is true:
1. They were a paying customer (past invoice, contract, project completion, or payment discussed)
2. Clear prior revenue intent — they received or requested a proposal, discussed specific pricing, or agreed to a project that did not start

DO NOT flag: cold outreach with no reply, general networking, informational conversations, leads that said "no", or contacts with no financial intent.

For qualifying contacts, analyze:
- The previous business relationship and what revenue was involved
- Why NOW is specifically a good time (seasonal, business cycle, new product fit, time since last contact)
- What specific offer would resonate based on their past interest

Generate a message that sounds like it came from a human who remembers the conversation — not a sales template.

Output ONLY valid JSON:
{
  "contactName": "string",
  "email": "string",
  "company": "string",
  "lastContactDate": "ISO date string",
  "history": "string (1-2 sentences: what was the previous business relationship)",
  "whyContact": "string (why this person, why now — specific seasonal or business reason, 2-3 sentences)",
  "suggestedOffer": "string (specific value proposition based on their previous interest)",
  "suggestedMessage": "string (3-4 sentences, human tone, references prior conversation, ends with a question)"
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
