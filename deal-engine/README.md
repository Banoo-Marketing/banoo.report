# Emod's Deal Engine

Autonomous outbound engine. Runs every 3 hours. Finds 2 warm or cold prospects, writes personalized emails via Claude, saves as Gmail drafts for Emod to review and send.

## Setup

### 1. Install
```bash
cd deal-engine
npm install
```

### 2. Get your Google refresh token
```bash
node src/get-token.js
```
Open the URL it prints, authorize Gmail access, paste the code back. Copy the `GOOGLE_REFRESH_TOKEN` it outputs.

### 3. Configure .env
```bash
cp .env.example .env
```
Fill in all values:
```
GOOGLE_CLIENT_ID=        # from Google Cloud Console
GOOGLE_CLIENT_SECRET=    # from Google Cloud Console
GOOGLE_REFRESH_TOKEN=    # from step 2 above
GMAIL_USER=emod@banoo.marketing
APOLLO_API_KEY=          # from apollo.io
ANTHROPIC_API_KEY=       # from console.anthropic.com
```

### 4. Run
```bash
# Run once (test mode)
npm run test:once

# Run continuously, every 3 hours
npm start
```

## How it works

Each run (every 3 hours):
1. **Gmail scan** — finds threads 60-90 days dormant matching marketing/ads/SEO topics → warm re-engage emails
2. **Apollo search** — finds PI lawyers in GTA/Ontario (Toronto, Mississauga, Brampton, Hamilton, Ottawa), solo to 20-person firms → cold authority emails
3. **Claude fallback** — if Apollo returns 0, Claude suggests 5 known small Ontario PI firms
4. **Email generation** — Claude writes personalized subject + body for each prospect
5. **Gmail drafts** — saves 2 drafts minimum to Gmail. Never auto-sends.

## Logs
Each run logs to `/logs/run_YYYY-MM-DD.txt`

## Google Cloud setup
- Project: `lead-gen-ai-457318`
- Enable: Gmail API + (optional) Calendar API
- OAuth 2.0 credentials → redirect URI: `https://developers.google.com/oauthplayground`
