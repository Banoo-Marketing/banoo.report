# SMB Context Pack

Your AI tools don't know your business. This fixes that.

---

## What it does

SMB Context Pack gives any AI tool — ChatGPT, Claude, Gemini — instant knowledge of your business.

Once set up, you copy one block of text and paste it before any question. The AI immediately knows:
- What your business does
- Who your clients are
- What you're focused on right now
- Your current risks and priorities
- Recent business events

No training. No API connections. No accounts.

---

## Quick Start

Run this from the `smb_context_pack` folder:

```
python onboarding/setup.py
```

Answer 5 questions. In under 3 minutes, you'll have a context block ready to paste into any AI tool.

**Already set up before?** Run quick mode — it auto-fills what it knows:

```
python onboarding/setup.py --quick
```

---

## How to Use with AI Tools

**Step 1:** Generate your context

```
python export_context.py
```

**Step 2:** Copy the text block that appears

**Step 3:** Paste it at the top of any AI conversation, before your question

**Example:**
```
[paste your context here]

Write a follow-up email for my top client.
```

The AI responds as if it already knows your business.

---

## Format Options

Different AI tools work better with different formats:

```
python export_context.py --chatgpt   # for ChatGPT
python export_context.py --claude    # for Claude
python export_context.py --gemini    # for Gemini
python export_context.py --save      # save to context.txt
```

---

## Adding Business Memory

Every time something important happens, log it:

```
python memory/log.py "Acme Corp" manual "Signed 3-month renewal"
python memory/log.py "RBC" manual "Balance low — mortgage payment due June 1"
python memory/log.py "John Smith" manual "Warm referral from City Plumbing"
```

Memory builds over time. Your context gets richer automatically.

**Types:** `manual` (you typed it) · `email` · `crm` · `system`

---

## Updating Your Business Profile

Edit the files in `company_profile/` directly:

| File | What it contains |
|---|---|
| `identity.json` | Company name, what you do, main offer, tone |
| `clients.json` | Active clients and their health status |
| `tone.json` | Communication style preferences |
| `offers.json` | Current offers and promotions |
| `services.json` | Core services |

**Client health values:** `ok` or `at_risk`

Example `clients.json`:
```json
{
  "active": [
    {"name": "Acme Corp", "health": "ok"},
    {"name": "City Plumbing", "health": "at_risk"}
  ]
}
```

---

## Checking Your Setup

Run the validator at any time:

```
python validate.py
```

This checks that your profile and memory are complete and correctly formatted.

---

## Folder Structure

```
smb_context_pack/
├── company_profile/   ← your business data (edit these)
├── memory/entries/    ← business memory (grows over time)
├── context_engine/    ← reads profile + memory, outputs state
├── api/               ← build_context() and get_context_string()
├── onboarding/        ← setup.py (run this first)
├── export_context.py  ← export your context string
└── validate.py        ← check your setup
```

---

## Core Principle

Memory is the moat. The more you log, the better your context becomes.

Every client update, deal, risk, and decision you record makes the AI more useful for your business.

---

## Frequently Asked Questions

**Does this send data anywhere?**
No. Everything runs locally on your machine. Nothing is uploaded or shared.

**How often should I run setup?**
Run `setup.py --quick` whenever your business focus changes — takes under a minute.

**How often should I add memory?**
After any significant client interaction, deal, or business event. Even one line is enough.

**Can I use this with multiple AI tools?**
Yes. Use `--chatgpt`, `--claude`, or `--gemini` to format for each tool. The information is the same — just the formatting changes.

**What if I make a mistake in setup?**
Run `python onboarding/setup.py` again. It auto-fills what you entered before — just correct what's wrong.
