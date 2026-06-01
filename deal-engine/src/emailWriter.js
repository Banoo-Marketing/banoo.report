'use strict'
const Anthropic = require('@anthropic-ai/sdk')

let _client = null
function getClient() {
  if (!_client) _client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })
  return _client
}

const SYSTEM = `You are Emod Vafa, founder of Banoo Marketing in Toronto. You write short, punchy outreach emails.

Rules:
- Subject line: specific, not generic (e.g. "Smith Law — Google Ads intake" not "Quick question")
- Body: max 4 lines
- Reference something specific about them (their firm, city, practice area)
- One clear CTA: 15-min call or "reply with interest"
- Never use "I hope this finds you well" or any filler
- Sign off exactly: "— Emod\nemod@banoo.ca | (416) 400-4699"
- Output format: Subject: [line]\n\n[body]`

async function generateEmail(prospect) {
  let prompt
  if (prospect.pathType === 'warm') {
    prompt = `Write a warm re-engagement email to ${prospect.name}${prospect.company ? ` at ${prospect.company}` : ''}.
Last contact: ${prospect.lastContact || '2-3 months ago'}.
Topic last discussed: ${prospect.topic || 'marketing'}.
CTA: "Want to reconnect this month?"`
  } else {
    prompt = `Write a cold outreach email to ${prospect.name}${prospect.company ? ` at ${prospect.company}` : ''}${prospect.city ? ` in ${prospect.city}` : ''}.
They are a personal injury ${prospect.title || 'lawyer'} in Ontario.
Pitch: I manage Google Ads and intake optimization for PI firms. I can drive more qualified case intake.
Be direct. Reference their specific type of firm.`
  }

  const msg = await getClient().messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 350,
    system: SYSTEM,
    messages: [{ role: 'user', content: prompt }],
  })

  const text = msg.content[0].text.trim()
  const subjectMatch = text.match(/^Subject:\s*(.+)/im)
  const subject = subjectMatch
    ? subjectMatch[1].trim()
    : `${prospect.company || prospect.name} — quick question`
  const body = text.replace(/^Subject:\s*.+\n?/im, '').trim()

  return { subject, body }
}

module.exports = { generateEmail }
