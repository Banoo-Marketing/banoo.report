'use strict'
const Anthropic = require('@anthropic-ai/sdk')
const { log } = require('./logger')

let _client = null
function getClient() {
  if (!_client) _client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })
  return _client
}

// Fallback when Apollo returns nothing — Claude reasons about known PI firm patterns
async function findPIFirmTargets() {
  try {
    const msg = await getClient().messages.create({
      model: 'claude-sonnet-4-6',
      max_tokens: 600,
      messages: [{
        role: 'user',
        content: `List 5 small personal injury law firms in Ontario, Canada (Toronto, Mississauga, Brampton, Hamilton, or Ottawa) with under 20 employees.

For each provide:
- Firm name (real, specific firm)
- City
- Best-guess contact email (info@firmname.ca or firstname@firmname.ca)
- One specific reason they need Google Ads / digital marketing

Return ONLY a JSON array, no other text:
[{"name":"...","city":"...","email":"...","reason":"..."}]`,
      }],
    })

    const text = msg.content[0].text
    const match = text.match(/\[[\s\S]*?\]/)
    if (match) return JSON.parse(match[0])
  } catch (err) {
    log('Claude firm search failed: ' + err.message)
  }
  return []
}

module.exports = { findPIFirmTargets }
