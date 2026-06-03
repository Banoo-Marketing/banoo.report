const Anthropic = require('@anthropic-ai/sdk');

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const COLD_SUBJECTS = [
  'Cases are being lost after intake—not before it',
  'Question about your unretained files',
  'Do you re-engage closed consultations?',
  'Advertising isn\'t the problem',
  'Curious how your firm handles old leads',
  'Former leads are hiring other firms',
  'Most PI firms underestimate this revenue leak',
  'Are old inquiries still being contacted?',
  'What firms are doing with dormant leads in 2026',
];

const SIGNATURE = 'Banoo Legal Marketing\n🇨🇦+1 (416) 400-4699';

const GROWTH_PLAN = 'Growth Plan for you:\nPPC, SEO, Email Marketing, Social Media, Lead Generation, CRM Cleanup.';

let subjectIndex = 0;
function nextSubject() {
  return COLD_SUBJECTS[subjectIndex++ % COLD_SUBJECTS.length];
}

/**
 * PATH A — warm re-engage: prospect had a prior Gmail/Calendar thread.
 */
async function writeWarmEmail(prospect) {
  const { name, email, lastContactDate, meetingTitle } = prospect;

  const firstName = name.split(' ')[0] || name;
  const dateStr = lastContactDate
    ? new Date(lastContactDate).toLocaleDateString('en-CA', { month: 'long', year: 'numeric' })
    : 'a few months ago';
  const context = meetingTitle ? `our meeting about "${meetingTitle}"` : `our conversation in ${dateStr}`;

  const prompt = `Write a short re-engagement email to ${firstName} (a personal injury lawyer).

Context:
- Last contact: ${dateStr}
- Prior context: ${context}
- Email to: ${email}

Requirements:
- Subject: one of these (pick the most relevant): ${COLD_SUBJECTS.join(' | ')}
- Body: 3-4 sentences MAX
- Reference the prior contact naturally
- CTA: simple — "Worth reconnecting in July?"
- Tone: warm, direct, peer-to-peer — no fluff
- No sender name anywhere in the body
- End with EXACTLY this on its own line: ${SIGNATURE}
- After the body and before the signature, add EXACTLY this block:
${GROWTH_PLAN}

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
  const { name, email, firmName, city, growthSignal, fitReason } = prospect;

  const firstName = name.split(' ')[0] || name;
  const firm = firmName ? ` at ${firmName}` : '';
  const location = city || 'Ontario';
  const signal = growthSignal ? `\n- Growth signal: ${growthSignal}` : '';
  const fit = fitReason ? `\n- Fit: ${fitReason}` : '';

  const prompt = `Write a short cold outreach email to ${firstName}${firm}, a personal injury lawyer in ${location}.

Context:${signal}${fit}

Requirements:
- Subject: one of these (pick the most relevant): ${COLD_SUBJECTS.join(' | ')}
- Body: 3-4 sentences MAX
- Reference something specific about them or their firm if available
- Core message: we work with PI firms on lead recovery and growth marketing
- CTA: ask if they re-engage old inquiries, or offer to share what firms are doing
- Tone: confident, peer-to-peer — no hype, no "I" or sender name in body
- No sender name anywhere in the body
- End with EXACTLY this on its own line: ${SIGNATURE}
- After the body and before the signature, add EXACTLY this block:
${GROWTH_PLAN}

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

  const subject = nextSubject();
  const fallbackBody =
    path === 'A'
      ? `Hey ${name},\n\nA lot has changed in PI lead gen this year. Most firms have more signed-case potential sitting in their CRM than in their ad account.\n\nAre you currently re-engaging inquiries from the last 12–24 months?\n\n${GROWTH_PLAN}\n\n${SIGNATURE}`
      : `Hey ${name},\n\nMost PI law firms — including firms like yours — have more signed-case potential sitting in their CRM than in their ad account.\n\nAre you currently re-engaging inquiries from the last 12–24 months?\n\n${GROWTH_PLAN}\n\n${SIGNATURE}`;

  return { to: toEmail, subject, body: fallbackBody, path };
}

async function generateEmail(prospect) {
  if (prospect.path === 'A') return writeWarmEmail(prospect);
  return writeColdEmail(prospect);
}

module.exports = { generateEmail };
