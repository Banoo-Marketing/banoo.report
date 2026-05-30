import { callClaudeJSON } from '@/lib/claude'
import type { EmailThread, OpportunitySignal } from '@/types'

const SYSTEM = `You are a revenue intelligence AI. Analyze email conversations to find business opportunities.

Detect: pricing requests, quote requests, service inquiries, proposals, buying intent, marketing needs, project discussions, referrals.

Opportunity Score (0-100):
- 81-100: Clear buying signal with budget/timeline confirmed
- 61-80: Strong interest, likely to convert
- 31-60: Possible opportunity, needs follow-up
- 0-30: No real opportunity (skip)

Revenue Confidence Score (0-100) — probability this specific action generates revenue:
- 90-100: Asked for pricing or proposal, recent conversation, budget confirmed
- 70-89: Engaged, asked questions, prior relationship
- 50-69: Moderate interest, stalled or needs nurturing
- 30-49: Weak signal, speculative

Output ONLY valid JSON:
{
  "contactName": "string",
  "company": "string",
  "opportunityScore": 0,
  "revenueConfidence": 0,
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
    result.revenueConfidence = Math.min(100, Math.max(0, result.revenueConfidence ?? result.opportunityScore))
    return result
  } catch {
    return null
  }
}
