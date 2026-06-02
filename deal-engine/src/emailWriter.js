const Anthropic = require('@anthropic-ai/sdk');

let _client = null;
function getClient() {
  if (!_client) _client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  return _client;
}

// ── Subject line pool — rotate per prospect ────────────────────────────────────
const SUBJECTS = [
  'Cases are being lost after intake—not before it',
  'Question about your unretained files',
  'Do you re-engage closed consultations?',
  'Advertising isn\'t the problem',
  'Curious how your firm handles old leads',
  'Former leads are hiring other firms',
  'Most firms underestimate this revenue leak',
  'Are old inquiries still being contacted?',
  'What firms are doing with dormant leads in 2026',
];

let _subjectIndex = 0;
function nextSubject() {
  const s = SUBJECTS[_subjectIndex % SUBJECTS.length];
  _subjectIndex++;
  return s;
}

// ── Fixed email body ───────────────────────────────────────────────────────────

function buildBody(firstName) {
  const greeting = (firstName && !isFirmName(firstName)) ? firstName : 'there';
  return `Hey ${greeting},

Most law firms have more signed-case potential sitting in their CRM than in their ad account.

While reviewing intake and follow-up processes across Ontario firms, a common pattern kept showing up: old inquiries, unsigned retainers, and dormant consultations often receive little or no follow-up after the initial conversation.

The result isn't a lead generation problem—it's a lead recovery problem.

Curious: do you currently have a process for re-engaging inquiries and consultations from the last 12–24 months?

If not, happy to share what we're seeing and where firms are typically uncovering additional signed cases without increasing ad spend.

Emod

Emod Vafa
Founder
Banoo Marketing
Toronto Legal Marketing`;
}

const FIRM_SIGNALS = ['llp', 'law', 'lawyers', 'legal', 'associates', 'partners',
                      'barristers', 'injury', 'family', 'litigation', 'inc', 'pc'];

function isFirmName(name) {
  const lower = (name || '').toLowerCase();
  return FIRM_SIGNALS.some(s => lower.includes(s));
}

function extractFirstName(fullName) {
  if (!fullName) return null;
  if (isFirmName(fullName)) return null;
  return fullName.split(' ')[0];
}

// ── Both paths use the same template ──────────────────────────────────────────

async function writeReengagementEmail(prospect, logger) {
  const firstName = prospect.first_name || extractFirstName(prospect.name);
  return { subject: nextSubject(), body: buildBody(firstName) };
}

async function writeColdEmail(prospect, logger) {
  const firstName = prospect.first_name || extractFirstName(prospect.name);
  return { subject: nextSubject(), body: buildBody(firstName) };
}

module.exports = { writeReengagementEmail, writeColdEmail };
