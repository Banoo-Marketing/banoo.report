# Decision Engine

Reads your business context. Tells you what to do today.

## What it does

Takes the SMB Context Pack snapshot and outputs four specific actions:

1. **REVENUE ACTION** — what moves money today
2. **RISK ACTION** — what prevents a loss today
3. **CLIENT ACTION** — what strengthens a client relationship today
4. **QUICK WIN** — low effort, high impact

Actions are named. Real clients. No vague advice.

## Run it

From `smb_context_pack/`:

```bash
# Actions + context (full daily briefing)
python decision_engine/decision_engine.py

# Actions only
python decision_engine/decision_engine.py --only

# With Claude-formatted context
python decision_engine/decision_engine.py --claude
```

Or via the existing context API:

```bash
python api/context.py --decisions
```

## Use it in code

```python
from decision_engine.decision_engine import generate_actions, get_full_output

# Full briefing string
print(get_full_output())

# Actions only
print(generate_actions())

# Append decisions to any context format
from api.context import get_context_string
prompt = get_context_string(fmt="claude", include_decisions=True)
```

## Rules

- Revenue actions come before risk. Risk before client.
- If a client is at-risk → recovery first.
- If revenue is weak → lead follow-up first.
- If clients are stable → upsell first.
- Always references real client names when available.
- Returns `NO ACTIONS AVAILABLE - MISSING CONTEXT` if context is broken.
