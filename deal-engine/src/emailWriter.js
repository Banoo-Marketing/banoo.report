'use strict'
const Anthropic = require('@anthropic-ai/sdk')

let _client = null
function getClient() {
  if (!_client) _client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })
  return _client
}

function buildEmail(prospect) {
  const firstName = prospect.firstName || null
  const greeting = firstName ? `Hi ${firstName},` : 'Hi,'

  const body = `${greeting}

How many injury inquiries from the past 20 months never signed a retainer?

Most PI firms have hundreds of old leads sitting in their CRM with little or no follow-up.

We help law firms reactivate old leads, automate follow-ups, improve CRM management, and generate more consultations.

The entire service is only $2K/month.

If we help recover just one additional case, the ROI is significant.

Worth a quick conversation?`

  const subject = `$2K/month to recover old injury leads?`

  return { subject, body }
}

async function generateEmail(prospect) {
  return buildEmail(prospect)
}

module.exports = { generateEmail }
