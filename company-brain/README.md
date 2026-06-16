# 🧠 Company Brain — AI Sales Co-Pilot

> AI-powered business co-pilot that monitors your CRM, detects renewals, coaches reps,
> and drafts emails — all requiring human approval before anything executes.

## Architecture

```
FastAPI (Python)  ←→  Claude API (claude-sonnet-4-6)
     ↓                       ↓
PostgreSQL + pgvector    Celery + Redis
     ↓
React Dashboard  ←→  WebSocket real-time alerts
```

## Quick Start

### 1. Clone & configure
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 2. Start everything
```bash
docker compose up -d
```

### 3. Seed mock data
```bash
docker compose exec api python seed_data.py
```

### 4. Open dashboard
```
http://localhost:3000
```

### 5. Trigger your first AI scan
Click **"🔍 Scan Renewals"** on the dashboard — Claude will draft renewal emails
for deals expiring soon and queue them for your approval.

---

## Services

| Service | URL | Purpose |
|---------|-----|---------|
| Dashboard | http://localhost:3000 | React UI |
| API | http://localhost:8000 | FastAPI |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Redis | localhost:6379 | Task queue |
| Postgres | localhost:5432 | Main DB |

---

## Key API Endpoints

```
GET  /alerts                    → pending approvals
POST /alerts/{id}/approve       → approve action
POST /alerts/{id}/reject        → reject with reason
GET  /deals                     → all deals
GET  /deals/{id}                → single deal
POST /deals/{id}/analyse        → run AI analysis on demand
POST /scan/renewals             → trigger renewal scan
POST /scan/agent                → trigger full AI scan
GET  /contacts/top              → top 20% by CLV
GET  /contacts/{id}/nurture     → get AI nurture suggestion
GET  /audit                     → audit log
WS   /ws/alerts                 → real-time alert push
```

---

## Human Approval Gate

**Nothing executes automatically.** Every AI-suggested action goes into `action_queue`
with status `PENDING_APPROVAL`. A human must click Approve in the dashboard (or via API)
before anything happens. This is enforced at the DB level — `execute_approved_action`
checks for an APPROVED record before running.

---

## Adding Real CRM Data

### HubSpot
```bash
# Set in .env:
HUBSPOT_PRIVATE_TOKEN=your-token

# Then call:
POST /connectors/hubspot/sync  # (build in connectors/hubspot.py)
```

### Gmail
```bash
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
# OAuth flow: GET /auth/google
```

---

## Folder Structure

```
company-brain/
├── docker-compose.yml
├── schema.sql              ← PostgreSQL schema
├── .env.example
├── backend/
│   ├── main.py             ← FastAPI app + WebSocket
│   ├── renewal_engine.py   ← Renewal detection + Claude email drafting
│   ├── clv_engine.py       ← CLV calculation + nurture suggestions
│   ├── agent_loop.py       ← Central AI decision engine
│   ├── tasks.py            ← Celery tasks (scheduled + on-demand)
│   ├── celery_app.py       ← Beat schedule config
│   ├── database.py         ← Postgres connection pool
│   ├── config.py           ← Settings (reads .env)
│   └── seed_data.py        ← Mock data generator
└── frontend/
    └── src/
        ├── App.jsx
        ├── pages/
        │   ├── Dashboard.jsx   ← Alert inbox + stat cards + scan triggers
        │   └── Deals.jsx       ← Deal list + AI analysis panel
        └── components/
            ├── AlertInbox.jsx  ← Pending approvals with one-click approve/reject
            ├── ApprovalModal.jsx ← Full email preview + approval flow
            └── DealCard.jsx    ← Deal summary card
```

---

## Cost Estimate (production)

| Item | Monthly |
|------|---------|
| Claude API (~500K tokens/day) | ~$150–300 |
| AWS t3.large | ~$80 |
| Redis | Free tier |
| **Total** | **~$250–400/mo** |

Built with: FastAPI · Claude API · PostgreSQL + pgvector · Celery · React
