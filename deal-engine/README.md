# Emod's Deal Engine

Autonomous outbound opportunity engine. Runs every 3 hours and creates 2 Gmail drafts targeting personal injury lawyers in Ontario.

## How It Works

Each run follows this priority order to find 2 prospects:

1. **Gmail** — dormant PI lawyer threads (no contact in 60–90 days) → PATH A warm re-engage
2. **Google Calendar** — past meeting attendees not followed up → PATH A warm re-engage
3. **Apollo.io** — cold search: PI lawyers in GTA/Ontario, solo to 20-person firms → PATH B cold authority
4. **Claude AI research** — identifies growing/hiring PI firms in Ontario → PATH B cold authority

Claude writes every email. Drafts land in your Gmail drafts folder — nothing is ever auto-sent.

## Setup

### 1. Install dependencies

```bash
cd deal-engine
npm install
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in `.env` (see below).

### 3. Get your Google refresh token

```bash
node setup-oauth.js
```

Open the URL in your browser, authorize with `emod@banoo.marketing`, paste the code back. Copy the printed `GOOGLE_REFRESH_TOKEN` into `.env`.

**Google Cloud project:** `lead-gen-ai-457318`  
**Required APIs:** Gmail API + Google Calendar API (both enabled in OAuth consent screen)  
**Scopes needed:** `gmail.modify`, `gmail.compose`, `calendar.readonly`

### 4. Add Apollo API key

Log in to Apollo.io → Settings → API Keys → copy into `.env` as `APOLLO_API_KEY`.

### 5. Run

```bash
# Single test run (runs immediately, no cron)
npm test

# Production (starts cron: every 3 hours, also runs once on startup)
npm start
```

## Environment Variables

| Variable | Description |
|---|---|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `GOOGLE_REFRESH_TOKEN` | Long-lived refresh token (from setup-oauth.js) |
| `SENDER_EMAIL` | `emod@banoo.marketing` |
| `APOLLO_API_KEY` | Apollo.io API key |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key |

## Folder Structure

```
deal-engine/
  src/
    index.js        — cron scheduler + orchestrator
    gmail.js        — Gmail OAuth, dormant contact scan, draft creation
    apollo.js       — Apollo.io prospect search
    search.js       — Claude AI web research
    emailWriter.js  — Claude email generation (PATH A/B)
    logger.js       — file-based run logging
  logs/             — run_[timestamp].txt per execution
  setup-oauth.js    — one-time OAuth token setup
  .env.example      — env template
  .env              — your secrets (never committed)
  package.json
  README.md
```

## Logs

Each run writes to `logs/run_[timestamp].txt` with prospects found, emails generated, and draft IDs.

## Email Paths

**PATH A — Warm Re-engage** (prior Gmail/Calendar thread found)
> References name, date of last contact, topic discussed.  
> CTA: "Want to reconnect in July?"

**PATH B — Cold Authority** (Apollo / web research)
> "I manage PPC/lead gen for top PI firms in Toronto/Ontario. Open to a quick chat?"  
> Includes their specific growth signal if available.
