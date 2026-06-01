const { google } = require('googleapis');

function getOAuthClient() {
  const oauth2Client = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    'urn:ietf:wg:oauth:2.0:oob'
  );
  oauth2Client.setCredentials({ refresh_token: process.env.GOOGLE_REFRESH_TOKEN });
  return oauth2Client;
}

function getGmailClient() {
  return google.gmail({ version: 'v1', auth: getOAuthClient() });
}

function getCalendarClient() {
  return google.calendar({ version: 'v3', auth: getOAuthClient() });
}

/**
 * Scan Gmail for PI lawyer-related threads dormant for 60-90 days.
 * Returns up to `limit` prospects with prior thread context.
 */
async function findDormantPIContacts(limit = 3) {
  const gmail = getGmailClient();
  const prospects = [];

  const now = new Date();
  const sixtyDaysAgo = new Date(now - 60 * 24 * 60 * 60 * 1000);
  const ninetyDaysAgo = new Date(now - 90 * 24 * 60 * 60 * 1000);

  const afterEpoch = Math.floor(ninetyDaysAgo.getTime() / 1000);
  const beforeEpoch = Math.floor(sixtyDaysAgo.getTime() / 1000);

  const query = `(personal injury OR "PI lawyer" OR "personal injury lawyer" OR "law firm" OR "legal" OR "intake") after:${afterEpoch} before:${beforeEpoch} -label:sent`;

  let threads;
  try {
    const res = await gmail.users.threads.list({
      userId: 'me',
      q: query,
      maxResults: 20,
    });
    threads = res.data.threads || [];
  } catch (err) {
    console.error('Gmail thread list error:', err.message);
    return [];
  }

  for (const thread of threads) {
    if (prospects.length >= limit) break;
    try {
      const t = await gmail.users.threads.get({ userId: 'me', id: thread.id });
      const messages = t.data.messages || [];
      if (!messages.length) continue;

      const lastMsg = messages[messages.length - 1];
      const headers = lastMsg.payload?.headers || [];
      const getHeader = (name) => headers.find((h) => h.name.toLowerCase() === name.toLowerCase())?.value || '';

      const from = getHeader('From');
      const subject = getHeader('Subject');
      const date = getHeader('Date');

      // Skip our own sent messages as the last contact
      if (from.toLowerCase().includes(process.env.SENDER_EMAIL?.toLowerCase() || 'emod@banoo.marketing')) continue;

      // Extract email address
      const emailMatch = from.match(/<(.+?)>/) || from.match(/\S+@\S+/);
      if (!emailMatch) continue;
      const email = emailMatch[1] || emailMatch[0];
      const name = from.replace(/<.+>/, '').trim().replace(/"/g, '') || email.split('@')[0];

      prospects.push({
        source: 'gmail',
        path: 'A',
        name,
        email,
        subject,
        lastContactDate: date,
        threadId: thread.id,
      });
    } catch (err) {
      // skip bad thread
    }
  }

  return prospects;
}

/**
 * Scan Google Calendar for past meeting attendees not followed up (last 90 days).
 */
async function findCalendarFollowUps(limit = 3) {
  const calendar = getCalendarClient();
  const prospects = [];

  const now = new Date();
  const ninetyDaysAgo = new Date(now - 90 * 24 * 60 * 60 * 1000);

  let events;
  try {
    const res = await calendar.events.list({
      calendarId: 'primary',
      timeMin: ninetyDaysAgo.toISOString(),
      timeMax: now.toISOString(),
      maxResults: 30,
      singleEvents: true,
      orderBy: 'startTime',
    });
    events = res.data.items || [];
  } catch (err) {
    console.error('Calendar list error:', err.message);
    return [];
  }

  const senderEmail = (process.env.SENDER_EMAIL || 'emod@banoo.marketing').toLowerCase();

  for (const event of events) {
    if (prospects.length >= limit) break;
    const attendees = event.attendees || [];
    for (const att of attendees) {
      if (att.email?.toLowerCase() === senderEmail) continue;
      if (att.responseStatus === 'declined') continue;
      prospects.push({
        source: 'calendar',
        path: 'A',
        name: att.displayName || att.email.split('@')[0],
        email: att.email,
        subject: `Re: ${event.summary || 'our meeting'}`,
        lastContactDate: event.start?.dateTime || event.start?.date,
        meetingTitle: event.summary,
      });
      if (prospects.length >= limit) break;
    }
  }

  return prospects;
}

/**
 * Create a Gmail draft.
 */
async function createDraft({ to, subject, body }) {
  const gmail = getGmailClient();
  const sender = process.env.SENDER_EMAIL || 'emod@banoo.marketing';

  const raw = [
    `From: Emod Vafa <${sender}>`,
    `To: ${to}`,
    `Subject: ${subject}`,
    `MIME-Version: 1.0`,
    `Content-Type: text/plain; charset=utf-8`,
    '',
    body,
  ].join('\r\n');

  const encoded = Buffer.from(raw).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

  const res = await gmail.users.drafts.create({
    userId: 'me',
    requestBody: { message: { raw: encoded } },
  });

  return res.data.id;
}

module.exports = { findDormantPIContacts, findCalendarFollowUps, createDraft };
