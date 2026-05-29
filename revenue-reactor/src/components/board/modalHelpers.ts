interface Draft { subject: string; body: string }

const PROMPTS: Record<string, string> = {
  opportunity: 'Write a concise, professional follow-up email expressing interest and proposing a next step (call or proposal). Keep it under 5 sentences.',
  churn: 'Write a caring, professional email to a client who may be unhappy. Address their concerns, offer a solution, and invite them to a quick call.',
  retention: 'Write a friendly check-in email to an existing client referencing their mentioned goal or milestone. Offer a helpful suggestion.',
  reactivation: 'Write a warm, non-pushy reactivation email referencing the previous conversation. Keep it brief and offer specific value.',
}

export async function callClaude(type: string, to: string, context: string): Promise<Draft> {
  const res = await fetch('/api/draft', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type, to, context, prompt: PROMPTS[type] }),
  })
  if (!res.ok) throw new Error('Draft failed')
  return res.json() as Promise<Draft>
}
