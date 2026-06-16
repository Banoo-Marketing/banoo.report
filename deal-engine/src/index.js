'use strict'
require('dotenv').config()
const cron = require('node-cron')
const { searchThreads, getThread, createDraft } = require('./gmail')
const { searchPILawyers } = require('./apollo')
const { findPIFirmTargets } = require('./search')
const { generateEmail } = require('./emailWriter')
const { log } = require('./logger')

// Track drafted emails within process lifetime to avoid duplicates
const drafted = new Set()

// ── Warm leads: Gmail threads dormant 60-90 days ──────────────────────────────

async function getWarmLeads() {
  const since = new Date()
  since.setDate(since.getDate() - 90)
  const until = new Date()
  until.setDate(until.getDate() - 60)

  const sinceStr = since.toISOString().slice(0, 10).replace(/-/g, '/')
  const untilStr = until.toISOString().slice(0, 10).replace(/-/g, '/')

  const threads = await searchThreads(
    `after:${sinceStr} before:${untilStr} -from:noreply -from:no-reply -from:notification (marketing OR ads OR SEO OR website OR campaign OR proposal)`,
    15
  )

  const leads = []
  for (const t of threads.slice(0, 6)) {
    try {
      const detail = await getThread(t.id)
      const msgs = detail.messages || []
      const first = msgs[0]?.payload?.headers || []
      const last  = msgs[msgs.length - 1]?.payload?.headers || []

      const from    = first.find(h => h.name === 'From')?.value || ''
      const subject = first.find(h => h.name === 'Subject')?.value || ''
      const date    = last.find(h => h.name === 'Date')?.value || ''

      if (/noreply|no-reply|newsletter|notification|@google|@linkedin|@facebook/i.test(from)) continue

      const email = from.match(/<([^>]+)>/)?.[1] || from.trim()
      const name  = from.replace(/<[^>]+>/, '').trim().replace(/"/g, '') || email.split('@')[0]

      if (!email.includes('@')) continue

      leads.push({ name, email, topic: subject, lastContact: date, pathType: 'warm' })
    } catch { /* skip bad threads */ }
  }
  return leads.slice(0, 3)
}

// ── Cold leads: Apollo → Claude fallback ──────────────────────────────────────

async function getColdLeads() {
  let prospects = await searchPILawyers()

  if (prospects.length === 0) {
    log('Apollo returned 0 results — using Claude fallback')
    const firms = await findPIFirmTargets()
    prospects = firms.map(f => ({
      name: 'Managing Partner',
      email: f.email,
      company: f.name,
      city: f.city,
      reason: f.reason,
      pathType: 'cold',
    }))
  }

  return prospects.filter(p => p.email && p.email.includes('@')).slice(0, 4)
}

// ── Main run ──────────────────────────────────────────────────────────────────

async function run() {
  const runTs = new Date().toISOString()
  log(`=== Deal Engine run: ${runTs} ===`)

  let draftsCreated = 0
  const results = []

  try {
    const [warm, cold] = await Promise.all([getWarmLeads(), getColdLeads()])
    log(`Warm leads: ${warm.length} | Cold prospects: ${cold.length}`)

    const candidates = [...warm, ...cold]

    for (const prospect of candidates) {
      if (draftsCreated >= 2) break
      if (drafted.has(prospect.email)) continue

      try {
        const { subject, body } = await generateEmail(prospect)
        const draft = await createDraft(prospect.email, subject, body)
        drafted.add(prospect.email)
        draftsCreated++
        results.push({ to: prospect.email, subject, draftId: draft.id })
        log(`✓ Draft: "${subject}" → ${prospect.email}`)
      } catch (err) {
        log(`✗ Failed ${prospect.email}: ${err.message}`)
      }
    }

    log(`Run done. ${draftsCreated}/2 drafts created.`, results)
  } catch (err) {
    log('Run error: ' + err.message)
  }
}

// ── Scheduler ─────────────────────────────────────────────────────────────────

run() // always run once on start

if (!process.env.RUN_ONCE) {
  cron.schedule('0 */3 * * *', () => {
    log('Cron fired — 3h interval')
    run()
  })
  log('Deal Engine running. Next auto-run in 3h. Ctrl+C to stop.')
}
