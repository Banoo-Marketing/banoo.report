interface Draft { subject: string; body: string }

export type DraftType = 'opportunity' | 'churn' | 'reactivation'

const PROMPTS: Record<DraftType, string> = {
  opportunity: 'Write a concise follow-up email. Reference the specific opportunity. Propose one clear next step (call, proposal, or demo). Sound like a real person — no buzzwords, no AI-speak. Max 150 words.',
  churn: 'Write a caring email to a client who may be unhappy. Acknowledge the issue directly, show empathy, and offer one specific solution or a quick call. Warm and human — not defensive or over-apologetic. Max 150 words.',
  reactivation: 'Write a warm reactivation email. Reference the previous conversation naturally. Give a specific reason why now is a good time to reconnect. Low-pressure call to action. Max 150 words.',
}

export const DRAFT_TYPE_LABELS: Record<DraftType, string> = {
  opportunity: 'Follow-Up',
  churn: 'Recovery',
  reactivation: 'Reactivation',
}

export async function callClaude(type: DraftType, to: string, context: string): Promise<Draft> {
  const res = await fetch('/api/draft', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type, to, context, prompt: PROMPTS[type] }),
  })
  if (!res.ok) throw new Error('Draft failed')
  return res.json() as Promise<Draft>
}
