// Subject pool — shuffled, no consecutive repeats
const SUBJECTS = [
  'Quick question about your old PI files',
  'Are former leads hiring other firms?',
  'Do you follow up on unsigned retainers?',
  'Most PI firms miss this revenue source',
  'Old injury inquiries — what happens to them?',
  'What GTA firms are doing with dormant leads',
];

let _pool = [];
let _lastSubject = null;

function nextSubject() {
  if (_pool.length === 0) {
    _pool = [...SUBJECTS];
    for (let i = _pool.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [_pool[i], _pool[j]] = [_pool[j], _pool[i]];
    }
  }
  // Avoid consecutive repeat
  if (_pool[_pool.length - 1] === _lastSubject && _pool.length > 1) {
    const top = _pool.pop();
    const idx = Math.floor(Math.random() * _pool.length);
    _pool.splice(idx, 0, top);
  }
  _lastSubject = _pool.pop();
  return _lastSubject;
}

// Email body — exact, no changes
const BODY = `Most PI firms have more signed-case potential sitting in old CRM contacts than in their current ad spend.

Are you re-engaging injury inquiries from the last 12–24 months?

Happy to share what GTA firms are doing to recover those cases.`;

// Signature — exact format
const SIGNATURE = `Emod Vafa
Banoo Marketing
banoo.marketing
+1 (416) 400-4699
cal.com/emodvafa`;

const FIRM_SIGNALS = ['llp', 'law', 'lawyers', 'legal', 'associates', 'partners',
                      'barristers', 'injury', 'family', 'litigation', 'inc', 'pc'];

function isFirmName(name) {
  return FIRM_SIGNALS.some(s => (name || '').toLowerCase().includes(s));
}

function extractFirstName(fullName) {
  if (!fullName || isFirmName(fullName)) return null;
  return fullName.split(' ')[0];
}

function buildEmail(prospect) {
  const firstName = prospect.first_name || extractFirstName(prospect.name);
  const greeting  = (firstName && firstName.trim()) ? `Hi ${firstName},` : 'Hi there,';
  return {
    subject: nextSubject(),
    body:    `${greeting}\n\n${BODY}\n\n${SIGNATURE}`,
  };
}

async function writeReengagementEmail(prospect, logger) {
  return buildEmail(prospect);
}

async function writeColdEmail(prospect, logger) {
  return buildEmail(prospect);
}

module.exports = { writeReengagementEmail, writeColdEmail };
