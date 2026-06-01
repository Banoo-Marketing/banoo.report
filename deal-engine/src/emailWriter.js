const Anthropic = require('@anthropic-ai/sdk');

let _client = null;
function getClient() {
  if (!_client) _client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  return _client;
}

const SYSTEM_PROMPT = `You are Emod Vafa, founder of Banoo Marketing — a Toronto-based digital marketing agency
specializing in Google Ads PPC and SEO for law firms.

Your credentials: personally managed Google Ads for Diamond & Diamond Lawyers and Preszler Law —
two of Toronto's highest-spending legal advertisers. You know exactly how the legal PPC market
in Ontario works.

You write outreach emails that are:
- 3-4 lines maximum (never longer)
- Personalized with a specific, accurate detail about the recipient
- One clear CTA (15-min call or reply with interest)
- Professional and direct — no fluff, no generic opener like "I hope this finds you well"
- From: Emod Vafa, Banoo Marketing | (416) 400-4699 | cal.com/emodvafa

Return ONLY a JSON object with keys "subject" and "body". No other text.`;

// ── PATH A: Warm re-engagement (dormant Gmail thread) ─────────────────────────

async function writeReengagementEmail(prospect, logger) {
  const prompt = `Write a warm re-engagement email for:

Name: ${prospect.name}
Email: ${prospect.email}
Firm: ${prospect.firm || 'their law firm'}
Context: ${prospect.context}

This is PATH A — we had a prior conversation. Reference the approximate timeframe and topic naturally.
CTA: suggest reconnecting in the next 2-3 weeks, offer cal.com/emodvafa for booking.

Return JSON: { "subject": "...", "body": "..." }`;

  return callClaude(prompt, logger);
}

// ── PATH B: Cold authority pitch (SEMrush / new prospect) ─────────────────────

async function writeColdEmail(prospect, logger) {
  const prompt = `Write a cold outreach email for:

Name: ${prospect.name}
Email: ${prospect.email}
Firm/Domain: ${prospect.firm || prospect.domain}
Context: ${prospect.context}

This is PATH B — cold outreach. Key angle: they're already spending on Google Ads (SEMrush shows
they advertise for "${prospect.keyword}"). Emod's pitch: I managed PPC for Diamond & Diamond and
Preszler Law — I know how to make legal PPC more efficient than what they're doing now.

Use a subject line that references something specific (their ad spend, their niche, their location).
Don't use "Hope this finds you well" or any generic opener.
CTA: 15-min call, link to cal.com/emodvafa.

Return JSON: { "subject": "...", "body": "..." }`;

  return callClaude(prompt, logger);
}

async function callClaude(prompt, logger) {
  const client = getClient();

  try {
    const msg = await client.messages.create({
      model:      'claude-sonnet-4-6',
      max_tokens: 400,
      system:     SYSTEM_PROMPT,
      messages:   [{ role: 'user', content: prompt }],
    });

    const text = msg.content[0].text.trim();

    // Strip markdown code block if present
    const clean = text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '').trim();
    return JSON.parse(clean);
  } catch (err) {
    logger.error('Claude email generation failed', { message: err.message });
    return null;
  }
}

module.exports = { writeReengagementEmail, writeColdEmail };
