'use strict'
const { google } = require('googleapis')
const { Buffer } = require('buffer')

function getAuth() {
  const client = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    'https://developers.google.com/oauthplayground'
  )
  client.setCredentials({ refresh_token: process.env.GOOGLE_REFRESH_TOKEN })
  return client
}

async function searchThreads(query, maxResults = 20) {
  const gmail = google.gmail({ version: 'v1', auth: getAuth() })
  const res = await gmail.users.threads.list({ userId: 'me', q: query, maxResults })
  return res.data.threads || []
}

async function getThread(threadId) {
  const gmail = google.gmail({ version: 'v1', auth: getAuth() })
  const res = await gmail.users.threads.get({
    userId: 'me', id: threadId, format: 'metadata',
    metadataHeaders: ['From', 'To', 'Subject', 'Date'],
  })
  return res.data
}

function buildRaw(to, subject, body) {
  const msg = [
    `From: Emod Vafa <${process.env.GMAIL_USER}>`,
    `To: ${to}`,
    `Subject: ${subject}`,
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=utf-8',
    '',
    body,
  ].join('\r\n')
  return Buffer.from(msg).toString('base64url')
}

async function createDraft(to, subject, body) {
  const gmail = google.gmail({ version: 'v1', auth: getAuth() })
  const res = await gmail.users.drafts.create({
    userId: 'me',
    requestBody: { message: { raw: buildRaw(to, subject, body) } },
  })
  return res.data
}

module.exports = { searchThreads, getThread, createDraft }
