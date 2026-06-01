/**
 * Run this ONCE to get your Google refresh token.
 * Usage: node src/get-token.js
 * Then copy the refresh token into your .env as GOOGLE_REFRESH_TOKEN=
 */
'use strict'
require('dotenv').config()
const { google } = require('googleapis')
const readline = require('readline')

const oauth2Client = new google.auth.OAuth2(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET,
  'https://developers.google.com/oauthplayground'
)

const SCOPES = [
  'https://www.googleapis.com/auth/gmail.compose',
  'https://www.googleapis.com/auth/gmail.readonly',
  'https://www.googleapis.com/auth/calendar.readonly',
]

const url = oauth2Client.generateAuthUrl({ access_type: 'offline', scope: SCOPES, prompt: 'consent' })

console.log('\n1. Open this URL in your browser:\n')
console.log(url)
console.log('\n2. Authorize the app, then paste the code from the redirect URL below.\n')

const rl = readline.createInterface({ input: process.stdin, output: process.stdout })
rl.question('Paste the authorization code: ', async (code) => {
  rl.close()
  const { tokens } = await oauth2Client.getToken(code)
  console.log('\n✓ Add this to your .env file:\n')
  console.log(`GOOGLE_REFRESH_TOKEN=${tokens.refresh_token}`)
})
