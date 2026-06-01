'use strict'
const Anthropic = require('@anthropic-ai/sdk')

let _client = null
function getClient() {
  if (!_client) _client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })
  return _client
}

function buildEmail(prospect) {
  const firstName = prospect.firstName || null
  const greeting = firstName ? `Hi ${firstName},` : 'Hi Team,'

  const body = `${greeting}

Any plan to reengage with your clients in June and July?

I help PI Law firms with their CRM, Email Marketing, Follow up with leads, PPC, SEO, Social Media, AI Visibility to find new clients and get in touch with their old leads.

Let me know if you see a value in a quick call.`

  const firm = prospect.company || prospect.name || 'your firm'
  const subject = `${firm} — June/July client reactivation`

  return { subject, body }
}

async function generateEmail(prospect) {
  return buildEmail(prospect)
}

module.exports = { generateEmail }
