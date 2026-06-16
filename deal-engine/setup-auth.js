/**
 * setup-auth.js — One-time OAuth2 setup to generate your Google refresh token.
 *
 * Run this ONCE on your local machine:
 *   node setup-auth.js
 *
 * It will:
 *   1. Start a local server on port 8000
 *   2. Print a URL — open it in your browser
 *   3. Sign in as emod@banoo.marketing (or emadvafa@gmail.com)
 *   4. Capture the auth code automatically
 *   5. Print your GOOGLE_REFRESH_TOKEN to paste into .env
 */

require('dotenv').config();

const http     = require('http');
const url      = require('url');
const { google } = require('googleapis');

const CLIENT_ID     = process.env.GOOGLE_CLIENT_ID     || '';
const CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET || '';
const REDIRECT_URI  = 'http://localhost:8000/auth/google/callback';
const PORT          = 8000;

const SCOPES = [
  'https://www.googleapis.com/auth/gmail.readonly',
  'https://www.googleapis.com/auth/gmail.compose',
];

if (!CLIENT_ID || !CLIENT_SECRET) {
  console.error('\n  ERROR: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be in your .env file');
  console.error('  Copy .env.example to .env and fill in your Google OAuth credentials first.\n');
  process.exit(1);
}

const oauth2Client = new google.auth.OAuth2(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI);

const authUrl = oauth2Client.generateAuthUrl({
  access_type: 'offline',
  scope:       SCOPES,
  prompt:      'consent',
});

console.log('\n  ┌─────────────────────────────────────────────────────────────┐');
console.log('  │  Deal Engine — Gmail OAuth Setup                            │');
console.log('  └─────────────────────────────────────────────────────────────┘');
console.log('\n  Step 1: Open this URL in your browser:\n');
console.log('  ' + authUrl);
console.log('\n  Step 2: Sign in as emod@banoo.marketing (or emadvafa@gmail.com)');
console.log('  Step 3: Click "Allow" — this page will update automatically\n');
console.log('  Waiting for authorization...\n');

const server = http.createServer(async (req, res) => {
  const parsed = url.parse(req.url, true);
  if (parsed.pathname !== '/auth/google/callback') {
    res.end('Not found');
    return;
  }

  const code  = parsed.query.code;
  const error = parsed.query.error;

  if (error) {
    res.end(`<h1>Error: ${error}</h1><p>Close this tab and try again.</p>`);
    server.close();
    process.exit(1);
  }

  if (!code) {
    res.end('<h1>No code received</h1>');
    server.close();
    process.exit(1);
  }

  try {
    const { tokens } = await oauth2Client.getToken(code);

    res.end(`
      <html><body style="font-family:sans-serif;max-width:600px;margin:40px auto;padding:20px">
        <h2>✓ Authorization successful</h2>
        <p>Your refresh token has been printed in the terminal. Close this tab.</p>
      </body></html>
    `);

    console.log('  ✓ Authorization successful!\n');
    console.log('  Add this to your .env file:\n');
    console.log(`  GOOGLE_REFRESH_TOKEN=${tokens.refresh_token}\n`);

    if (!tokens.refresh_token) {
      console.log('  ⚠  No refresh_token returned — try revoking access at');
      console.log('     https://myaccount.google.com/permissions');
      console.log('     then run setup again.\n');
    }
  } catch (err) {
    res.end(`<h1>Token exchange failed</h1><pre>${err.message}</pre>`);
    console.error('  Token exchange error:', err.message);
  }

  server.close();
});

server.listen(PORT, () => {
  console.log(`  Local auth server running on http://localhost:${PORT}`);
});
