interface Draft { subject: string; body: string }

export type DraftType = 'opportunity' | 'churn' | 'reactivation' | 'referral'

const PROMPTS: Record<DraftType, string> = {
  opportunity: 'Write a concise, professional follow-up email. Reference the specific opportunity mentioned. Propose a clear next step (call, proposal, or demo). Keep it under 5 sentences. No generic AI language — make it sound like a real person wrote it.',
  churn: 'Write a caring, professional email to a client who may be unhappy. Acknowledge the issue directly, show empathy, and offer a specific solution or quick call. Do not be defensive or overly apologetic. Keep it warm and human.',
  reactivation: 'Write a warm, brief reactivation email. Reference the previous conversation naturally. Give a specific reason why now is a good time to reconnect. Include a clear but low-pressure CTA. 3-4 sentences max.',
  referral: 'Write a friendly email asking for a referral from a happy client. Keep it short, make it easy to forward, and include a brief reminder of the value delivered. 3-4 sentences. Casual and genuine tone.',
}

export const DRAFT_TYPE_LABELS: Record<DraftType, string> = {
  opportunity: 'Follow-Up',
  churn: 'Churn Recovery',
  reactivation: 'Reactivation',
  referral: 'Referral Request',
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
