const Anthropic = require('@anthropic-ai/sdk');

let _client = null;
function getClient() {
  if (!_client) _client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  return _client;
}

// ── Email template ─────────────────────────────────────────────────────────────
// Fixed body structure — only first name and subject are personalized.

function buildBody(firstName) {
  const greeting = firstName && firstName !== 'there' ? firstName : 'Team';
  return `Hi ${greeting}

Any plan to reengage with your clients in June and July?

I help PI Law firms with their CRM, Email Marketing, Follow up with leads, PPC, SEO, Social Media, AI Visibility to find new clients and get in touch with their old leads.

Let me know if you see value in a quick call`;
}

// ── Subject generation via Claude ──────────────────────────────────────────────
// Body is fixed. Only the subject line is AI-generated to be specific to the firm.

const SUBJECT_SYSTEM = `You write subject lines for cold outreach emails targeting personal injury law firms in Ontario.
The email is from Emod Vafa at Banoo Marketing (emod@banoo.ca).

Rules:
- Short: 6-10 words max
- Specific to their firm, city, or niche — not generic
- No clickbait, no all-caps, no exclamation marks
- Do NOT use "Hope this finds you" or similar
- Examples of good subjects:
  "Quick question — PI lead gen for [Firm]"
  "Toronto PI firms + client reactivation — worth a chat?"
  "Your [City] PI practice + summer pipeline"

Return ONLY the subject line as plain text. No quotes, no JSON.`;

async function getSubject(prospect, logger) {
  const client = getClient();
  const prompt = `Write a subject line for a cold outreach email to:
Firm: ${prospect.firm || prospect.name}
City: ${prospect.city || 'Ontario'}
Context: ${prospect.context || 'PI law firm'}`;

  try {
    const msg = await client.messages.create({
      model:      'claude-sonnet-4-6',
      max_tokens: 30,
      system:     SUBJECT_SYSTEM,
      messages:   [{ role: 'user', content: prompt }],
    });
    return msg.content[0].text.trim().replace(/^["']|["']$/g, '');
  } catch (err) {
    logger.error('Subject generation failed', { message: err.message });
    return `PI lead gen — worth a quick chat, ${prospect.firm || prospect.city || 'Ontario'}?`;
  }
}

// ── PATH A: Warm re-engagement ─────────────────────────────────────────────────

async function writeReengagementEmail(prospect, logger) {
  const firstName = prospect.first_name || extractFirstName(prospect.name);
  const subject   = await getSubject(prospect, logger);
  const body      = buildBody(firstName);
  return { subject, body };
}

// ── PATH B: Cold outreach ──────────────────────────────────────────────────────

async function writeColdEmail(prospect, logger) {
  const firstName = prospect.first_name || extractFirstName(prospect.name);
  const subject   = await getSubject(prospect, logger);
  const body      = buildBody(firstName);
  return { subject, body };
}

const FIRM_SIGNALS = ['llp', 'law', 'lawyers', 'legal', 'associates', 'partners', 'barristers', 'injury'];

function extractFirstName(fullName) {
  if (!fullName || fullName === 'there') return null;
  const lower = fullName.toLowerCase();
  // If it looks like a firm name, use "Team"
  if (FIRM_SIGNALS.some(s => lower.includes(s))) return null;
  return fullName.split(' ')[0];
}

module.exports = { writeReengagementEmail, writeColdEmail };
