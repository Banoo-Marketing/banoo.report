import { callClaudeJSON } from '@/lib/claude'
import type { EmailThread, OpportunitySignal } from '@/types'

const SYSTEM = `You are a revenue intelligence AI. Analyze email conversations to find business opportunities.

Detect: pricing requests, quote requests, service inquiries, proposals, confirmed buying intent, budget discussions.

DO NOT flag: casual networking, vague interest with no ask, cold outreach with no reply, general information requests.

Opportunity Score (0-100):
- 81-100: Clear buying signal — budget/timeline confirmed, proposal requested
- 61-80: Strong intent — direct question about pricing or availability
- 0-60: Skip. Not actionable today.

Revenue Confidence Score (0-100) — probability this specific follow-up generates revenue:
- 90-100: Proposal requested, budget confirmed, timeline stated
- 70-89: Specific pricing question asked, prior relationship, active conversation
- 0-69: Speculative — skip.

Required evidence: you MUST cite specific quotes or actions from the conversation. If you cannot cite concrete evidence, set opportunityScore to 0.

Use imperative language in suggestedAction. Never use: "consider", "you may", "might", "could", "possibly".
Examples: "Send proposal today", "Call [Name] today", "Reply with pricing today", "Follow up by end of day".

Output ONLY valid JSON:
{
  "contactName": "string",
  "company": "string",
  "opportunityScore": 0,
  "revenueConfidence": 0,
  "estimatedValue": "string (e.g. '$3,000–$8,000' or 'Unknown')",
  "reason": "string (1-2 sentences: what specific thing happened that signals a real opportunity)",
  "evidence": ["string — direct quote or specific action from the conversation"],
  "suggestedAction": "string (imperative, specific, today-focused)"
}`

export async function findOpportunity(thread: EmailThread, userEmail: string): Promise<OpportunitySignal | null> {
  const conversation = thread.messages
    .map(m => `From: ${m.from}\nDate: ${m.sentAt.toISOString()}\n${m.bodyText.slice(0, 1500)}`)
    .join('\n---\n')

  try {
    const result = await callClaudeJSON<OpportunitySignal>(SYSTEM,
      `User email: ${userEmail}\nThread: "${thread.subject}"\nParticipants: ${thread.participants.slice(0, 5).join(', ')}\n\n${conversation.slice(0, 6000)}`)
    // Raise bar: require score ≥ 50 AND non-empty evidence for signal quality
    if (result.opportunityScore < 50 || !result.evidence || result.evidence.length === 0) return null
    result.revenueConfidence = Math.min(100, Math.max(0, result.revenueConfidence ?? result.opportunityScore))
    return result
  } catch {
    return null
  }
}
