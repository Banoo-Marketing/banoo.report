// ── Subject line pool — shuffled A/B rotation ────────────────────────────────
const SUBJECTS = [
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

// Fisher-Yates shuffle for true A/B rotation — no repeats until full cycle
let _pool = [];
function nextSubject() {
  if (_pool.length === 0) {
    _pool = [...SUBJECTS];
    for (let i = _pool.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [_pool[i], _pool[j]] = [_pool[j], _pool[i]];
    }
  }
  return _pool.pop();
}

// ── Email body ────────────────────────────────────────────────────────────────

function buildBody(firstName) {
  const greeting = (firstName && !isFirmName(firstName)) ? firstName : 'there';
  return `Hey ${greeting},

Most law firms have more signed-case potential sitting in their CRM than in their ad account.

While reviewing intake and follow-up processes across Ontario firms, a common pattern kept showing up: old inquiries, unsigned retainers, and dormant consultations often receive little or no follow-up after the initial conversation.

The result isn't a lead generation problem—it's a lead recovery problem.

Curious: do you currently have a process for re-engaging inquiries and consultations from the last 12–24 months?

If not, happy to share what we're seeing and where firms are typically uncovering additional signed cases without increasing ad spend.

Growth Plan for you:
PPC, SEO, Email Marketing, Social Media, Lead Generation, CRM Cleanup.

Banoo Legal Marketing
🇨🇦+1 (416) 400-4699`;
}

const FIRM_SIGNALS = ['llp', 'law', 'lawyers', 'legal', 'associates', 'partners',
                      'barristers', 'injury', 'family', 'litigation', 'inc', 'pc'];

function isFirmName(name) {
  return FIRM_SIGNALS.some(s => (name || '').toLowerCase().includes(s));
}

function extractFirstName(fullName) {
  if (!fullName || isFirmName(fullName)) return null;
  return fullName.split(' ')[0];
}

// ── Exports ───────────────────────────────────────────────────────────────────

async function writeReengagementEmail(prospect, logger) {
  const firstName = prospect.first_name || extractFirstName(prospect.name);
  return { subject: nextSubject(), body: buildBody(firstName) };
}

async function writeColdEmail(prospect, logger) {
  const firstName = prospect.first_name || extractFirstName(prospect.name);
  return { subject: nextSubject(), body: buildBody(firstName) };
}

module.exports = { writeReengagementEmail, writeColdEmail };
