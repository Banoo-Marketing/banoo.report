/**
 * search.js — Claude-powered prospect discovery fallback.
 * Used when Apollo/SEMrush are unavailable (IP not whitelisted).
 */

const Anthropic = require('@anthropic-ai/sdk');

let _client = null;
function getClient() {
  if (!_client) _client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  return _client;
}

const KNOWN_FIRMS = [
  'Diamond and Diamond', 'Preszler', 'Fosters Law',
  'Fasken', 'McCarthy Tetrault', 'Blakes', 'Osler', 'Stikeman', 'Borden Ladner',
  'Norton Rose', 'Dentons', 'Gowling',
];

// Rotate through provinces to get variety across runs
const PROVINCE_POOL = [
  { province: 'Ontario',          cities: 'Toronto, Ottawa, Hamilton, Mississauga',  area: 'family law and litigation' },
  { province: 'Alberta',          cities: 'Calgary, Edmonton',                       area: 'family law and litigation' },
  { province: 'British Columbia', cities: 'Vancouver, Surrey, Victoria',             area: 'family law and litigation' },
  { province: 'Nova Scotia',      cities: 'Halifax, Dartmouth',                      area: 'family law, litigation, and personal injury' },
];

let _provinceIndex = 0;

async function findNewProspects(count = 4, logger) {
  const client = getClient();

  // Rotate through provinces so each run targets a different region
  const targets = [];
  for (let i = 0; i < 2; i++) {
    targets.push(PROVINCE_POOL[_provinceIndex % PROVINCE_POOL.length]);
    _provinceIndex++;
  }

  logger.info('Claude fallback: generating prospect list', {
    provinces: targets.map(t => t.province).join(', '),
  });

  const prompt = `Generate a JSON array of ${count} real Canadian law firms that would be strong candidates
for Banoo Marketing's lead recovery and CRM re-engagement service.

Target provinces and practice areas:
${targets.map(t => `- ${t.province}: ${t.area} — cities: ${t.cities}`).join('\n')}

Criteria:
- Boutique to mid-size (2–30 lawyers)
- Family law, divorce, litigation, or civil litigation focus
- Nova Scotia firms: also include PI firms in Halifax/Atlantic
- NOT these already-known firms: ${KNOWN_FIRMS.join(', ')}
- Firms that likely accumulate dormant leads (high consultation volume)

For each firm return:
{
  "name": "firm name or contact person name",
  "first_name": "first name if known, else null",
  "email": "info@domain or best guess",
  "firm": "firm name",
  "domain": "domain.com",
  "city": "city",
  "province": "province abbreviation (ON/AB/BC/NS)",
  "practice": "family law|litigation|PI",
  "size": "solo|boutique|mid",
  "context": "1-sentence about why they accumulate dormant leads",
  "path": "B",
  "source": "claude-research"
}

Return ONLY the JSON array. No other text.`;

  try {
    const msg = await client.messages.create({
      model:      'claude-sonnet-4-6',
      max_tokens: 1200,
      messages:   [{ role: 'user', content: prompt }],
    });

    const text  = msg.content[0].text.trim();
    const clean = text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '').trim();
    const firms = JSON.parse(clean);

    logger.info(`Claude returned ${firms.length} prospects`);
    return Array.isArray(firms) ? firms : [];
  } catch (err) {
    logger.error('Claude prospect search failed', { message: err.message });
    return [];
  }
}

module.exports = { findNewProspects };
