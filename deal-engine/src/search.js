/**
 * search.js — Claude-powered PI firm discovery fallback.
 *
 * Used when SEMrush is unavailable (IP not whitelisted) or returns no results.
 * Generates a fresh list of Ontario PI law firms to target using Claude.
 */

const Anthropic = require('@anthropic-ai/sdk');

let _client = null;
function getClient() {
  if (!_client) _client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  return _client;
}

// Firms already in the pipeline — Claude will exclude these
const KNOWN_FIRMS = [
  'Diamond and Diamond', 'Preszler Law', 'Fosters Law',
  'Grillo Law', 'Schiffmann', 'Sokoloff', 'Longo Lawyers',
  'Karapancev', 'Kain & Ball', 'Omulique', 'Poonah', 'De Krupe',
];

async function findNewProspects(count = 5, logger) {
  const client = getClient();
  logger.info('Claude fallback: generating PI firm prospect list');

  const prompt = `Generate a JSON array of ${count} real Ontario personal injury law firms
that would be strong candidates for Google Ads PPC management by Banoo Marketing.

Criteria:
- Ontario-based (Toronto, Mississauga, Brampton, Hamilton, Ottawa, GTA)
- Personal injury focus (car accidents, slip & fall, catastrophic injury)
- Solo to 20-person boutique firms
- NOT already in pipeline: ${KNOWN_FIRMS.join(', ')}

For each firm return:
{
  "name": "firm name",
  "email": "best guess contact email (info@domain.com)",
  "domain": "domain.com",
  "firm": "firm name",
  "city": "city",
  "size": "solo|boutique|mid",
  "why": "1-line reason they need PPC (specific to their situation)",
  "path": "B",
  "source": "claude-research",
  "context": "Boutique PI firm in [city] — [specific insight about their situation]",
  "keyword": "personal injury lawyer [city]"
}

Return ONLY the JSON array. No other text.`;

  try {
    const msg = await client.messages.create({
      model:      'claude-sonnet-4-6',
      max_tokens: 1000,
      messages:   [{ role: 'user', content: prompt }],
    });

    const text  = msg.content[0].text.trim();
    const clean = text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '').trim();
    const firms = JSON.parse(clean);

    logger.info(`Claude returned ${firms.length} prospect firms`);
    return Array.isArray(firms) ? firms : [];
  } catch (err) {
    logger.error('Claude prospect search failed', { message: err.message });
    return [];
  }
}

module.exports = { findNewProspects };
