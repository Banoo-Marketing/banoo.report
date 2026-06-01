/**
 * Run this ONCE to get your Google refresh token.
 * Usage: node setup-oauth.js
 *
 * 1. Copy the URL printed to your browser
 * 2. Authorize the app
 * 3. Paste the code back here
 * 4. Copy the refresh_token into your .env as GOOGLE_REFRESH_TOKEN=
 */
require('dotenv').config();
const { google } = require('googleapis');
const readline = require('readline');

const oauth2Client = new google.auth.OAuth2(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET,
  'urn:ietf:wg:oauth:2.0:oob'
);

const SCOPES = [
  'https://www.googleapis.com/auth/gmail.modify',
  'https://www.googleapis.com/auth/gmail.compose',
  'https://www.googleapis.com/auth/calendar.readonly',
];

const authUrl = oauth2Client.generateAuthUrl({
  access_type: 'offline',
  scope: SCOPES,
  prompt: 'consent',
});

console.log('\n=== Google OAuth Setup ===');
console.log('1. Open this URL in your browser:\n');
console.log(authUrl);
console.log('\n2. Authorize, then paste the code below:\n');

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
rl.question('Enter the authorization code: ', async (code) => {
  rl.close();
  try {
    const { tokens } = await oauth2Client.getToken(code.trim());
    console.log('\n=== SUCCESS ===');
    console.log('Add this to your .env file:\n');
    console.log(`GOOGLE_REFRESH_TOKEN=${tokens.refresh_token}`);
  } catch (err) {
    console.error('Error getting tokens:', err.message);
  }
});
