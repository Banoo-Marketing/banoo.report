# Revenue Radar

**Find money hiding in Gmail.**

Revenue Radar is a Gmail-first AI revenue intelligence system that surfaces missed opportunities, detects churn risk, finds stalled deals, and generates reactivation outreach — all from your existing email conversations.

## Features

- **Opportunity Detection** — AI identifies pricing requests, proposal discussions, and buying intent
- **Missed Follow-up Detection** — Finds conversations where you need to follow up
- **Churn Risk Detection** — Detects at-risk clients before they leave
- **Reactivation Engine** — Surfaces past clients worth re-engaging
- **One-Click Email Drafts** — Claude generates professional emails for every signal
- **Daily Revenue Report** — Morning summary of your entire pipeline

## Tech Stack

- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: Next.js API routes
- **Database**: PostgreSQL + Prisma ORM
- **Auth**: NextAuth.js with Google OAuth (gmail.readonly scope)
- **AI**: Claude API (`claude-sonnet-4-6`)
- **Jobs**: Vercel Cron
- **Cache**: Upstash Redis (optional)

## Setup

### Prerequisites

- Node.js 18+
- PostgreSQL database
- Google Cloud project with Gmail API enabled
- Anthropic API key

### 1. Clone and install

```bash
cd revenue-radar
npm install
```

### 2. Configure environment variables

```bash
cp .env.example .env.local
```

Fill in all values in `.env.local`:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `NEXTAUTH_SECRET` | Random secret (min 32 chars) — generate with `openssl rand -base64 32` |
| `NEXTAUTH_URL` | Your app URL (e.g. `http://localhost:3000`) |
| `GOOGLE_CLIENT_ID` | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud Console |
| `ANTHROPIC_API_KEY` | From console.anthropic.com |
| `UPSTASH_REDIS_REST_URL` | Optional — from upstash.com |
| `UPSTASH_REDIS_REST_TOKEN` | Optional — from upstash.com |
| `ENCRYPTION_KEY` | 64 hex chars (32 bytes) — generate with `openssl rand -hex 32` |
| `CRON_SECRET` | Random secret for cron job protection |

### 3. Set up Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable the **Gmail API**
4. Go to **APIs & Services > Credentials > Create Credentials > OAuth 2.0 Client ID**
5. Add authorized redirect URIs:
   - `http://localhost:3000/api/auth/callback/google` (development)
   - `https://yourdomain.com/api/auth/callback/google` (production)
6. Copy Client ID and Client Secret to `.env.local`

### 4. Set up the database

```bash
# Push schema to database
npm run db:push

# Generate Prisma client
npm run db:generate

# (Optional) Seed with demo data
npm run db:seed
```

### 5. Run the development server

```bash
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000)

### 6. Connect Gmail

1. Sign in with your Google account
2. Grant Gmail read permission
3. Click "Sync Now" to analyze your inbox
4. Revenue opportunities will appear within 2-3 minutes

## Architecture

```
Google OAuth
    ↓
Gmail API (incremental sync via historyId)
    ↓
Email Filter (isHumanConversation classifier)
    ↓
Claude AI Agents (5 parallel analyzers)
    ↓
PostgreSQL (structured signals)
    ↓
Dashboard UI (4-tab interface)
    ↓
Email Draft → User Approval → Gmail Send
```

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/gmail/connect` | GET | Check Gmail connection status |
| `/api/gmail/sync` | POST | Trigger incremental sync |
| `/api/dashboard` | GET | Get dashboard metrics |
| `/api/opportunities` | GET | List opportunity signals |
| `/api/churn` | GET | List churn signals |
| `/api/reactivation` | GET | List reactivation contacts |
| `/api/email/draft` | POST | Generate AI email draft |
| `/api/email/send` | POST | Send approved email via Gmail |
| `/api/search` | GET | Search across all signals |
| `/api/jobs/sync` | GET | Cron: sync all users (protected) |
| `/api/jobs/daily-report` | GET | Cron: generate daily reports (protected) |

## Background Jobs

Vercel Cron runs two jobs automatically:

- **Every 10 minutes**: Incremental Gmail sync + AI processing
- **Every morning at 8am**: Daily revenue report generation

Cron endpoints are protected by the `CRON_SECRET` environment variable (passed as `Authorization: Bearer <secret>` header).

## Security

- OAuth tokens encrypted with AES-256-CBC before storage
- All API routes require authenticated session
- Email bodies stored only as summaries (max 5000 chars, cleared after processing)
- No email content exposed outside authenticated user context
- Cron endpoints protected by shared secret

## Deployment (Vercel)

```bash
vercel deploy
```

Set all environment variables in your Vercel project settings. Cron jobs will run automatically based on `vercel.json` schedule.

## Development

```bash
npm run dev          # Start dev server
npm run typecheck    # TypeScript check
npm run lint         # ESLint
npm run db:studio    # Prisma Studio (DB viewer)
```
