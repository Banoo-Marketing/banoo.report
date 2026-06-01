const Anthropic = require('@anthropic-ai/sdk');

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

/**
 * PATH A — warm re-engage: prospect had a prior Gmail/Calendar thread.
 */
async function writeWarmEmail(prospect) {
  const { name, email, subject, lastContactDate, meetingTitle, threadId } = prospect;

  const firstName = name.split(' ')[0] || name;
  const dateStr = lastContactDate
    ? new Date(lastContactDate).toLocaleDateString('en-CA', { month: 'long', year: 'numeric' })
    : 'a few months ago';
  const context = meetingTitle ? `our meeting about "${meetingTitle}"` : `our conversation in ${dateStr}`;

  const prompt = `Write a short, professional re-engagement email from Emod Vafa at Banoo Marketing to ${firstName} (a personal injury lawyer).

Context:
- Last contact: ${dateStr}
- Prior context: ${context}
- Email to: ${email}

Requirements:
- Subject line: personalized, references the prior conversation (NOT generic)
- Body: 3-4 lines MAX
- Reference something specific about the prior contact naturally
- CTA: "Want to reconnect in July?" or similar — one simple ask
- Tone: warm, direct, confident — not salesy
- Sign off: Emod Vafa, Banoo Marketing

Respond ONLY with JSON (no markdown):
{
  "subject": "...",
  "body": "..."
}`;

  const msg = await client.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 512,
    messages: [{ role: 'user', content: prompt }],
  });

  return parseEmailJSON(msg.content[0]?.text, email, firstName, 'A');
}

/**
 * PATH B — cold authority: no prior contact, prospect from Apollo or web research.
 */
async function writeColdEmail(prospect) {
  const { name, email, firmName, city, title, growthSignal, fitReason } = prospect;

  const firstName = name.split(' ')[0] || name;
  const firm = firmName ? ` at ${firmName}` : '';
  const location = city || 'Ontario';
  const signal = growthSignal ? `\n- Growth signal: ${growthSignal}` : '';
  const fit = fitReason ? `\n- Fit: ${fitReason}` : '';

  const prompt = `Write a short cold outreach email from Emod Vafa at Banoo Marketing to ${firstName}${firm}, a personal injury lawyer in ${location}.

Context:${signal}${fit}

Requirements:
- Subject line: specific, not generic (no "Quick question" or "Following up")
- Body: 3-4 lines MAX
- Reference something specific about them or their firm (use the growth signal if available)
- Core message: Emod manages PPC and lead gen for top PI firms in Toronto/Ontario
- CTA: one clear ask — offer a 15-min call or ask them to reply with interest
- Tone: confident authority, peer-to-peer — not salesy, no hype
- Sign off: Emod Vafa, Banoo Marketing | cal.com/emodvafa

Respond ONLY with JSON (no markdown):
{
  "subject": "...",
  "body": "..."
}`;

  const msg = await client.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 512,
    messages: [{ role: 'user', content: prompt }],
  });

  return parseEmailJSON(msg.content[0]?.text, email, firstName, 'B');
}

function parseEmailJSON(text, toEmail, name, path) {
  try {
    const jsonMatch = text?.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0]);
      return { to: toEmail, subject: parsed.subject, body: parsed.body, path };
    }
  } catch {
    // fallback below
  }

  // Fallback if Claude returns unexpected format
  const fallbackSubject = path === 'A' ? `Reconnecting — Emod Vafa` : `PI Lead Gen for ${name}'s Firm`;
  const fallbackBody =
    path === 'A'
      ? `Hi ${name},\n\nI was thinking about our last conversation and wanted to check in. A lot has changed in PI lead gen this year — want to reconnect in July for a quick chat?\n\nEmod Vafa\nBanoo Marketing`
      : `Hi ${name},\n\nI manage PPC and lead gen for top PI firms in Toronto/Ontario. We help firms like yours generate consistent intake without the guesswork.\n\nOpen to a 15-min call to see if there's a fit?\n\nEmod Vafa\nBanoo Marketing | cal.com/emodvafa`;

  return { to: toEmail, subject: fallbackSubject, body: fallbackBody, path };
}

async function generateEmail(prospect) {
  if (prospect.path === 'A') return writeWarmEmail(prospect);
  return writeColdEmail(prospect);
}

module.exports = { generateEmail };
