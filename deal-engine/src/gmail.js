const { google } = require('googleapis');

const SCOPES = [
  'https://www.googleapis.com/auth/gmail.readonly',
  'https://www.googleapis.com/auth/gmail.compose',
];

function getAuth() {
  const oauth2 = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    'http://localhost:8000/auth/google/callback'
  );
  oauth2.setCredentials({ refresh_token: process.env.GOOGLE_REFRESH_TOKEN });
  return oauth2;
}

function getGmail() {
  return google.gmail({ version: 'v1', auth: getAuth() });
}

// ── Dormant thread scanning ────────────────────────────────────────────────────

const PI_KEYWORDS = [
  'personal injury', 'accident lawyer', 'injury lawyer', 'law firm',
  'barrister', 'solicitor', 'legal services', 'ppc', 'google ads',
  'lead gen', 'marketing', 'accident', 'injury',
];

const DOMAIN_SIGNALS = ['law', 'legal', 'llp', 'barrister', 'attorney', 'injury'];

function looksLikeLegalContact(msg) {
  const from    = (msg.from || '').toLowerCase();
  const subject = (msg.subject || '').toLowerCase();
  const snippet = (msg.snippet || '').toLowerCase();
  const text    = from + ' ' + subject + ' ' + snippet;

  return (
    DOMAIN_SIGNALS.some(s => from.includes(s)) ||
    PI_KEYWORDS.some(k => text.includes(k))
  );
}

async function scanDormantContacts(logger) {
  const gmail   = getGmail();
  const results = [];

  // Threads where we had contact 60-180 days ago with no recent follow-up
  const nowSec     = Math.floor(Date.now() / 1000);
  const cutoffOld  = nowSec - 180 * 86400; // 180 days ago
  const cutoffNew  = nowSec - 60  * 86400; // 60 days ago

  const query = `after:${cutoffOld} before:${cutoffNew} -in:spam -in:trash`;

  logger.info('Scanning Gmail for dormant contacts', { query });

  let threads;
  try {
    const res = await gmail.users.threads.list({
      userId: 'me',
      q:      query,
      maxResults: 50,
    });
    threads = res.data.threads || [];
  } catch (err) {
    logger.error('Gmail scan failed', { message: err.message });
    return results;
  }

  logger.info(`Found ${threads.length} threads in range — filtering for PI/legal signals`);

  for (const thread of threads) {
    if (results.length >= 5) break;

    try {
      const detail = await gmail.users.threads.get({
        userId: 'me',
        id:     thread.id,
        format: 'metadata',
        metadataHeaders: ['From', 'To', 'Subject', 'Date'],
      });

      const messages = detail.data.messages || [];
      const last     = messages[messages.length - 1];
      if (!last) continue;

      const headers  = Object.fromEntries(
        last.payload.headers.map(h => [h.name, h.value])
      );

      const from     = headers['From']    || '';
      const subject  = headers['Subject'] || '';
      const snippet  = last.snippet       || '';

      if (!looksLikeLegalContact({ from, subject, snippet })) continue;

      // Check that we haven't already emailed them recently
      const lastDate  = new Date(headers['Date']);
      const daysSince = (Date.now() - lastDate) / 86400000;

      if (daysSince < 60) continue;

      const emailMatch = from.match(/<(.+?)>/) || [null, from.trim()];
      const email      = emailMatch[1];
      const name       = from.replace(/<.+>/, '').trim().replace(/"/g, '') || 'there';

      if (!email || email.includes('noreply') || email.includes('no-reply')) continue;

      results.push({
        name,
        email,
        firm:    extractFirmFromEmail(email),
        subject: subject.replace(/^(Re:|Fwd:|FW:|RE:)\s*/i, '').trim(),
        daysAgo: Math.round(daysSince),
        path:    'A',
        source:  'gmail',
        context: `Last contact ~${Math.round(daysSince)} days ago. Subject: "${subject}"`,
      });

      logger.info(`Dormant contact found: ${name} <${email}> (${Math.round(daysSince)}d ago)`);
    } catch (_) {
      // skip thread on error
    }
  }

  return results;
}

function extractFirmFromEmail(email) {
  const domain = email.split('@')[1] || '';
  return domain
    .replace(/\.(com|ca|org|net|law)$/i, '')
    .replace(/[-_]/g, ' ')
    .split('.')
    .join(' ');
}

// ── Draft creation ─────────────────────────────────────────────────────────────

async function createDraft(to, subject, body, logger) {
  const gmail = getGmail();

  const raw = Buffer.from(
    [
      `From: Emod Vafa <${process.env.SENDER_EMAIL}>`,
      `To: ${to}`,
      `Subject: ${subject}`,
      'Content-Type: text/plain; charset=utf-8',
      '',
      body,
    ].join('\r\n')
  ).toString('base64url');

  const draft = await gmail.users.drafts.create({
    userId:      'me',
    requestBody: { message: { raw } },
  });

  return draft.data.id;
}

module.exports = { scanDormantContacts, createDraft, SCOPES };
