/**
 * exchange-code.js — Exchange a manually pasted OAuth code for a refresh token.
 * Usage: node exchange-code.js "<code from redirect URL>"
 */
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const { google } = require('googleapis');

const code = process.argv[2];
if (!code) {
  console.error('Usage: node exchange-code.js "<code>"');
  process.exit(1);
}

const oauth2Client = new google.auth.OAuth2(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET,
  'http://localhost:8000/auth/google/callback'
);

oauth2Client.getToken(code).then(({ tokens }) => {
  if (!tokens.refresh_token) {
    console.error('No refresh_token returned. Revoke access at https://myaccount.google.com/permissions and try again with a fresh code.');
    process.exit(1);
  }

  const envPath = path.join(__dirname, '.env');
  let env = fs.readFileSync(envPath, 'utf8');
  env = env.replace(/GOOGLE_REFRESH_TOKEN=.*/, `GOOGLE_REFRESH_TOKEN=${tokens.refresh_token}`);
  fs.writeFileSync(envPath, env);

  console.log('Refresh token saved to .env');
}).catch(err => {
  console.error('Token exchange failed:', err.response?.data || err.message);
  process.exit(1);
});
