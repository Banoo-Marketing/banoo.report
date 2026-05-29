import { callClaudeJSON } from '@/lib/claude'
import type { EmailThread, OpportunityResult } from '@/types'

const SYSTEM_PROMPT = `You are a revenue intelligence AI that analyzes email conversations to detect business opportunities.

You identify signals like:
- Requests for pricing or quotes
- Proposal discussions
- Buying intent or readiness to purchase
- Hiring or staffing needs
- Marketing or service needs
- Referrals and introductions
- Business expansion discussions
- Interest in new products/services

Output ONLY a JSON object in this exact format:
{
  "contact_name": "string",
  "company": "string",
  "opportunity_score": number (0-100),
  "estimated_value": "string (e.g. '$5,000-$10,000' or 'Unknown')",
  "reason": "string",
  "evidence": ["string"],
  "recommended_action": "string"
}

If no opportunity exists, return opportunity_score: 0 and explain in reason.`

export async function detectOpportunity(thread: EmailThread, userEmail: string): Promise<OpportunityResult | null> {
  const conversationText = thread.messages
    .map(m => `From: ${m.from}\nDate: ${m.sentAt.toISOString()}\nBody:\n${m.bodyText.slice(0, 2000)}`)
    .join('\n\n---\n\n')

  const userPrompt = `Analyze this email thread for revenue opportunities.

User email (the business owner): ${userEmail}
Thread subject: ${thread.subject}
Participants: ${thread.participants.join(', ')}

Conversation:
${conversationText.slice(0, 8000)}`

  try {
    const result = await callClaudeJSON<OpportunityResult>(SYSTEM_PROMPT, userPrompt)
    if (result.opportunity_score < 30) return null
    return result
  } catch {
    return null
  }
}
