import { callClaudeJSON } from '@/lib/claude'
import type { EmailThread, OpportunitySignal } from '@/types'

const SYSTEM = `You are a revenue intelligence AI. Analyze email conversations to find business opportunities.

Detect: pricing requests, quote requests, service inquiries, proposals, buying intent, marketing needs, project discussions, referrals.

Score 0-100 where:
- 81-100: Clear buying signal with budget/timeline
- 61-80: Strong interest, likely to convert
- 31-60: Possible opportunity, needs follow-up
- 0-30: No real opportunity (return this score to indicate skip)

Output ONLY valid JSON:
{
  "contactName": "string",
  "company": "string",
  "opportunityScore": 0,
  "estimatedValue": "string (e.g. '$3,000-$8,000' or 'Unknown')",
  "reason": "string (1-2 sentences with specific evidence)",
  "evidence": ["string", "string"],
  "suggestedAction": "string (specific next step)"
}`

export async function findOpportunity(thread: EmailThread, userEmail: string): Promise<OpportunitySignal | null> {
  const conversation = thread.messages
    .map(m => `From: ${m.from}\nDate: ${m.sentAt.toISOString()}\n${m.bodyText.slice(0, 1500)}`)
    .join('\n---\n')

  try {
    const result = await callClaudeJSON<OpportunitySignal>(SYSTEM,
      `User email: ${userEmail}\nThread: "${thread.subject}"\nParticipants: ${thread.participants.slice(0, 5).join(', ')}\n\n${conversation.slice(0, 6000)}`)
    if (result.opportunityScore < 31) return null
    return result
  } catch {
    return null
  }
}
