const Anthropic = require('@anthropic-ai/sdk');

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const COLD_SUBJECTS = [
  'Quick question about your old PI files',
  'Are former leads hiring other firms?',
  'Do you follow up on unsigned retainers?',
  'Most PI firms miss this revenue source',
  'Old injury inquiries — what happens to them?',
  'What GTA firms are doing with dormant leads',
];

const SIGNATURE = `Emod Vafa
Banoo Marketing
banoo.marketing
+1 (416) 400-4699
cal.com/emodvafa`;

const BODY = `Most PI firms have more signed-case potential sitting in old CRM contacts than in their current ad spend.

Are you re-engaging injury inquiries from the last 12–24 months?

Happy to share what GTA firms are doing to recover those cases.`;

let lastSubjectIndex = -1;
function nextSubject() {
  let index;
  do {
    index = Math.floor(Math.random() * COLD_SUBJECTS.length);
  } while (index === lastSubjectIndex && COLD_SUBJECTS.length > 1);
  lastSubjectIndex = index;
  return COLD_SUBJECTS[index];
}

function greeting(name) {
  const first = name && name.split(' ')[0].trim();
  return first ? `Hi ${first},` : 'Hi there,';
}

/**
 * PATH A — warm re-engage: prospect had a prior Gmail/Calendar thread.
 */
async function writeWarmEmail(prospect) {
  const { name, email, lastContactDate, meetingTitle } = prospect;

  const dateStr = lastContactDate
    ? new Date(lastContactDate).toLocaleDateString('en-CA', { month: 'long', year: 'numeric' })
    : 'a few months ago';
  const context = meetingTitle ? `our meeting about "${meetingTitle}"` : `our conversation in ${dateStr}`;

  const prompt = `Write a short re-engagement email to a personal injury lawyer.

Context:
- Last contact: ${dateStr}
- Prior context: ${context}
- Email to: ${email}

Requirements:
- Subject: choose the most fitting from: ${COLD_SUBJECTS.join(' | ')}
- Greeting: "${greeting(name)}"
- Body (max 5 lines, plain text only, no bold/underline):
${BODY}
- Then on a new line, add the signature exactly as:
${SIGNATURE}
- No services list, no pricing, no "Growth Plan"

Respond ONLY with JSON (no markdown):
{
  "subject": "...",
  "body": "..."
}`;

  const msg = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 512,
    messages: [{ role: 'user', content: prompt }],
  });

  return parseEmailJSON(msg.content[0]?.text, email, name, 'A');
}

/**
 * PATH B — cold authority: no prior contact, prospect from Apollo or web research.
 */
async function writeColdEmail(prospect) {
  const { name, email, firmName, city } = prospect;

  const location = city || 'Ontario';
  const firm = firmName ? ` at ${firmName}` : '';

  const prompt = `Write a short cold outreach email to a personal injury lawyer${firm} in ${location}.

Requirements:
- Subject: choose the most fitting from: ${COLD_SUBJECTS.join(' | ')}
- Greeting: "${greeting(name)}"
- Body (max 5 lines, plain text only, no bold/underline):
${BODY}
- Then on a new line, add the signature exactly as:
${SIGNATURE}
- No services list, no pricing, no "Growth Plan"

Respond ONLY with JSON (no markdown):
{
  "subject": "...",
  "body": "..."
}`;

  const msg = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 512,
    messages: [{ role: 'user', content: prompt }],
  });

  return parseEmailJSON(msg.content[0]?.text, email, name, 'B');
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
  const fallbackBody = `${greeting(name)}

${BODY}

${SIGNATURE}`;

  return { to: toEmail, subject, body: fallbackBody, path };
}

async function generateEmail(prospect) {
  if (prospect.path === 'A') return writeWarmEmail(prospect);
  return writeColdEmail(prospect);
}

module.exports = { generateEmail };
