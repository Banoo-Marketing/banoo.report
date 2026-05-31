#!/usr/bin/env node
// Revenue Reactivation Engine
// Usage: node money-list.js

'use strict'

const fs = require('fs')
const path = require('path')

const ROOT = __dirname

const SKIP = new Set([
  'revenue-radar', 'revenue-reactor', 'templates', 'node_modules', '.git', 'CNAME',
  'money-list.js', 'package.json', 'package-lock.json', 'README.md',
])

// Known emails from past communications
const KNOWN_EMAILS = {
  'nfcr':                   'JFelts@nfcr.org',
  'vegain':                 'edan@vegain.ca',
  'Gus':                    'jon.isaak@gusdesigngroup.com',
  'developmentca':          'saath@getbuildify.com',
  'angelink':               null,
  '416Flower':              null,
  'FostersLaw':             null,
  'cafeconvo':              null,
  'lakeside-landscaping':   null,
  'ccl-group':              null,
}

// Human-readable names for email subjects / bodies
const DISPLAY_NAMES = {
  '416Flower':               '416 Flower',
  'FostersLaw':              'Foster\'s Law',
  'afcr':                    'AFCR',
  'angelink':                'Angelink',
  'nfcr':                    'NFCR',
  'craig-petronella':        'Craig Petronella',
  'developmentca':           'Developments.ca',
  'ccl-group':               'CCL Group',
  'TGB':                     'Toronto Gold Bullion',
  'aim-hi':                  'Aim Hi',
  'cafeconvo':               'Cafe Convo',
  'vegain':                  'Vegain',
  'lakeside-landscaping':    'Lakeside Landscaping',
  'groundscapesolution':     'GroundScape Solutions',
  'proinsulationcontracting':'Pro Insulation',
  'dubaicondo':              'Dubai Condo',
  'digitalmarketingink':     'Digital Marketing Ink',
  'Gus':                     'GUS Design',
  'cenan':                   'Cenan Bakery',
  'soclogix':                'SOClogix',
  'CrossRealms':             'CrossRealms',
  'feelsynergy':             'Feel Synergy',
  'BrownStone':              'BrownStone',
  'macdillions-global-energy':'Macdillion\'s Energy',
  'Seaspan':                 'Seaspan',
  'kimiya':                  'Kimiya',
  'ecogentis':               'Ecogentis',
  'cottage-septic-and-plumbing': 'Cottage Septic',
  'SAIT':                    'SAIT',
}

// Month name → 0-indexed month number
const MONTH_MAP = {
  jan:0, feb:1, mar:2, apr:3, may:4, jun:5, jul:6, aug:7, sep:8, oct:9, nov:10, dec:11,
  january:0, february:1, march:2, april:3, june:5, july:6, august:7,
  september:8, october:9, november:10, december:11,
}

const MONTH_RE = /(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)/i
const YEAR_RE  = /(202[3-9])/

// ─── Helpers ─────────────────────────────────────────────────────────────────

function readAllHtml(clientPath, maxBytes = 20000) {
  let content = ''
  try {
    function walk(dir) {
      for (const f of fs.readdirSync(dir)) {
        if (content.length > maxBytes) return
        const full = path.join(dir, f)
        let stat
        try { stat = fs.statSync(full) } catch { continue }
        if (stat.isDirectory() && !SKIP.has(f)) walk(full)
        else if (f.endsWith('.html')) {
          try { content += fs.readFileSync(full, 'utf8').slice(0, 4000) } catch { /* skip */ }
        }
      }
    }
    walk(clientPath)
  } catch { /* skip */ }
  return content.toLowerCase()
}

function getMonthFolders(clientPath) {
  try {
    return fs.readdirSync(clientPath).filter(f => {
      const full = path.join(clientPath, f)
      try { return fs.statSync(full).isDirectory() } catch { return false }
    }).filter(f => MONTH_RE.test(f) || YEAR_RE.test(f))
  } catch { return [] }
}

function parseMonthDate(folderName) {
  const lower = folderName.toLowerCase()
  const mMatch = lower.match(MONTH_RE)
  const yMatch = lower.match(YEAR_RE)
  if (mMatch && yMatch) {
    return new Date(parseInt(yMatch[1]), MONTH_MAP[mMatch[1]], 1)
  }
  return null
}

function latestMonth(folders) {
  let latest = null
  for (const f of folders) {
    const d = parseMonthDate(f)
    if (d && (!latest || d > latest)) latest = d
  }
  return latest
}

function daysSince(date) {
  if (!date) return null
  return Math.floor((Date.now() - date.getTime()) / 86400000)
}

function monthsActive(folders) {
  // each month folder = 1 month of service
  return folders.length
}

// ─── Score ───────────────────────────────────────────────────────────────────

function score(c) {
  let s = 0
  const months = c.monthCount
  const days = c.daysSilent

  // Was a real paying client
  if (months >= 6) s += 40
  else if (months >= 3) s += 35
  else if (months >= 1) s += 20

  // Service type (higher = more value)
  if (c.hasAds) s += 25
  if (c.hasSeo) s += 15
  if (c.hasRetainer) s += 10

  // Proposal sent but never converted
  if (c.hasProposal && months === 0) s += 20

  // Silence urgency
  if (days !== null) {
    if (days > 240) s += 20   // 8+ months quiet
    else if (days > 180) s += 15
    else if (days > 90)  s += 10
  } else if (c.hasProposal) {
    s += 15  // proposal without date = warm guess
  }

  return s
}

function estimateValue(c) {
  if (c.hasAds && c.monthCount >= 3) return '$2,000–$5,000/mo'
  if (c.hasAds)                      return '$1,500–$3,000/mo'
  if (c.hasSeo && c.monthCount >= 6) return '$1,500–$3,000/mo'
  if (c.hasSeo && c.monthCount >= 3) return '$1,000–$2,500/mo'
  if (c.monthCount >= 3)             return '$1,000–$2,500/mo'
  if (c.hasProposal)                 return '$1,000–$2,000/mo'
  return '$500–$1,500/mo'
}

function whyWarm(c) {
  const parts = []
  if (c.monthCount >= 6) parts.push(`${c.monthCount}-month client`)
  else if (c.monthCount >= 1) parts.push(`${c.monthCount}-month client`)
  if (c.hasAds) parts.push('ran paid ads')
  if (c.hasSeo) parts.push('active SEO')
  if (c.hasProposal && c.monthCount === 0) parts.push('proposal sent, never started')
  if (c.daysSilent !== null) {
    const mo = Math.round(c.daysSilent / 30)
    parts.push(`${mo}mo silent`)
  }
  return parts.join(' · ') || 'past relationship'
}

function reactivationAngle(c) {
  if (c.hasProposal && c.monthCount === 0) {
    return 'Close original proposal — follow up, simplify scope if needed'
  }
  if (c.hasAds && c.daysSilent > 180) {
    return 'Restart ad campaigns — budgets reset in Q2, fast ROI'
  }
  if (c.hasSeo && c.daysSilent > 180) {
    return 'Resume SEO — rankings erode without consistent work'
  }
  if (c.monthCount >= 6) {
    return 'Long-term client — strongest reactivation odds'
  }
  if (c.monthCount >= 3) {
    return 'Proven results exist — remind them what was working'
  }
  return 'Re-engage — context and trust already built'
}

// ─── Email Generator ──────────────────────────────────────────────────────────

function generateEmail(c) {
  const n = c.displayName
  let subject, body

  if (c.hasProposal && c.monthCount === 0) {
    subject = `${n} — still relevant?`
    body = `Hi,

Following up on the proposal we put together for ${n}.

Is this still something you're considering, or should I close it on my side?

Happy to simplify the scope if priorities have changed.

— Emod`
  } else if (c.hasAds) {
    subject = `${n} — ad campaigns`
    body = `Hi,

Checking in on the paid media we managed for ${n}.

Still running ads, or did things change on your end?

If paused, I can put together a quick restart plan.

— Emod`
  } else if (c.monthCount >= 3) {
    subject = `${n} — quick check-in`
    body = `Hi,

Checking in on ${n}. We had good momentum going on the marketing side.

Is the work still active, or did priorities shift?

10 minutes to reconnect if helpful.

— Emod`
  } else {
    subject = `${n} — still a priority?`
    body = `Hi,

Following up on our last conversation about ${n}.

Is marketing still a focus for you this year, or should I close the loop?

— Emod`
  }

  return {
    to: c.email || '[find email]',
    subject,
    body,
  }
}

// ─── Main ─────────────────────────────────────────────────────────────────────

const clients = []

for (const dir of fs.readdirSync(ROOT)) {
  if (SKIP.has(dir) || dir.startsWith('.')) continue
  const fullPath = path.join(ROOT, dir)
  let stat
  try { stat = fs.statSync(fullPath) } catch { continue }
  if (!stat.isDirectory()) continue

  const monthFolders = getMonthFolders(fullPath)
  const content      = readAllHtml(fullPath)
  const lastMonth    = latestMonth(monthFolders)
  const silent       = daysSince(lastMonth)

  // Skip completely empty folders with no HTML and no month folders
  if (content.length < 50 && monthFolders.length === 0) continue

  const hasAds      = /google.ads|meta.ads|bing.ads|facebook.ads|paid.media|\bppc\b|campaign.performance|ad.spend/i.test(content)
  const hasSeo      = /\bseo\b|organic.traffic|search.engine|keyword/i.test(content)
  const hasRetainer = /retainer|monthly.services|monthly.fee/i.test(content)
  const hasProposal = /proposal|scope.of.work|quote/i.test(content) ||
                      fs.readdirSync(fullPath).some(f => /proposal/i.test(f))

  const c = {
    name:        dir,
    displayName: DISPLAY_NAMES[dir] ?? dir,
    email:       KNOWN_EMAILS[dir] ?? null,
    monthCount: monthsActive(monthFolders),
    monthFolders,
    hasAds,
    hasSeo,
    hasRetainer,
    hasProposal,
    lastMonth,
    daysSilent: silent,
  }

  c.score              = score(c)
  c.estimatedValue     = estimateValue(c)
  c.whyWarm            = whyWarm(c)
  c.reactivationAngle  = reactivationAngle(c)

  if (c.score >= 20) clients.push(c)
}

const ranked = clients.sort((a, b) => b.score - a.score)
const top10  = ranked.slice(0, 10)
const top5   = ranked.slice(0, 5)

// ─── Print Output ─────────────────────────────────────────────────────────────

const W = 100
const LINE = '─'.repeat(W)

const pad = (s, n) => String(s).slice(0, n).padEnd(n)

console.log()
console.log(LINE)
console.log(`REVENUE REACTIVATION ENGINE  ·  ${new Date().toDateString().toUpperCase()}`)
console.log(LINE)

console.log('\n📋  TOP 10 MONEY LIST\n')
console.log(pad('CLIENT', 24) + pad('SCORE', 7) + pad('LAST ACTIVE', 14) + pad('WHY WARM', 40) + 'EST VALUE')
console.log('─'.repeat(W))

for (const c of top10) {
  const lastActive = c.lastMonth
    ? c.lastMonth.toLocaleString('default', { month: 'short', year: 'numeric' })
    : c.hasProposal ? 'Proposal only' : '—'
  console.log(
    pad(c.displayName, 24) +
    pad(c.score, 7) +
    pad(lastActive, 14) +
    pad(c.whyWarm, 40) +
    c.estimatedValue,
  )
}

console.log('\n' + LINE)
console.log('\n⚡  TOP 5 ACTION TARGETS\n')
for (let i = 0; i < top5.length; i++) {
  const c = top5[i]
  console.log(`  ${i + 1}. ${c.displayName}`)
  console.log(`     Action:  ${c.reactivationAngle}`)
  console.log(`     Value:   ${c.estimatedValue}  ·  ${c.whyWarm}`)
  console.log()
}

console.log(LINE)
console.log('\n✉️   EMAIL DRAFTS (TOP 5)\n')
for (let i = 0; i < top5.length; i++) {
  const c = top5[i]
  const email = generateEmail(c)
  console.log(`${'─'.repeat(50)}`)
  console.log(`EMAIL ${i + 1}: ${c.displayName}`)
  console.log(`TO:      ${email.to}`)
  console.log(`SUBJECT: ${email.subject}`)
  console.log()
  console.log(email.body)
}

console.log('\n' + LINE)
console.log(`\nTotal clients scanned: ${clients.length}  ·  Use output above to send emails today.\n`)
