# Revenue Reactor

A single-page Gmail revenue intelligence tool. Connect your Gmail inbox and instantly see new opportunities, churn risks, retention insights, and reactivation targets — all on one scrollable board.

## Setup

```bash
cp .env.example .env.local
npm install
npx prisma db push
npm run dev
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `NEXTAUTH_SECRET` | Random secret for NextAuth |
| `NEXTAUTH_URL` | App URL (e.g. http://localhost:3000) |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `ENCRYPTION_KEY` | 64 hex chars for AES-256 token encryption |
| `CRON_SECRET` | Secret header for cron endpoints |

## Architecture

- **Next.js 14** (App Router) + TypeScript
- **PostgreSQL** + Prisma ORM
- **NextAuth.js** with Google OAuth (gmail.readonly scope)
- **Claude** (`claude-sonnet-4-6`) for AI analysis
- **Vercel Cron** — sync every 10 min, monthly outreach list on 1st of month

## Revenue Board

Single scrollable page at `/board`:

1. **Opportunities** — leads, quotes, proposals detected in inbox
2. **Churn Risks** — clients showing signs they may leave
3. **Retention Opportunities** — ways to strengthen existing relationships
4. **Reactivation Targets** — old clients and inactive leads
5. **Monthly Outreach List** — top 20 contacts with personalized messages

Click any action button to generate an AI email draft. Copy to clipboard or open in Gmail — no auto-send.
