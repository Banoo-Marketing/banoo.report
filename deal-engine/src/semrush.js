const axios = require('axios');

const SEMRUSH_BASE = 'https://api.semrush.com/';

// PI keywords to find Ontario firms actively spending on Google Ads
const TARGET_PHRASES = [
  'personal injury lawyer toronto',
  'personal injury lawyer ontario',
  'accident lawyer toronto',
  'car accident lawyer toronto',
  'slip and fall lawyer toronto',
  'personal injury lawyer mississauga',
  'personal injury lawyer brampton',
  'personal injury lawyer hamilton',
];

// Domains to exclude (already known competitors or current clients)
const EXCLUDE_DOMAINS = [
  'diamondlaw.ca',
  'preszlerlaw.ca',
  'preszlerinjurylaw.com',
  'fosterslawyers.com',
];

async function findPIAdvertisers(logger) {
  const key = process.env.SEMRUSH_API_KEY;
  if (!key) {
    logger.warn('SEMRUSH_API_KEY not set — skipping SEMrush discovery');
    return [];
  }

  const results = [];
  const seen    = new Set(EXCLUDE_DOMAINS);

  for (const phrase of TARGET_PHRASES) {
    if (results.length >= 10) break;

    try {
      const params = new URLSearchParams({
        type:            'phrase_adwords',
        key,
        phrase,
        database:        'ca',
        export_columns:  'Dn,Po,Tr,Cp,Co',
        display_limit:   '10',
        display_sort:    'tr_desc',
      });

      const res  = await axios.get(`${SEMRUSH_BASE}?${params}`);
      const rows = parseSemrushCSV(res.data);

      for (const row of rows) {
        const domain = (row.Domain || '').toLowerCase().trim();
        if (!domain || seen.has(domain)) continue;

        seen.add(domain);
        results.push({
          domain,
          position:    row.Position,
          traffic:     row['Traffic (%)'],
          cpc:         row['CPC (USD)'],
          competition: row['Competition'],
          keyword:     phrase,
          email:       guessFirmEmail(domain),
          name:        domainToName(domain),
          firm:        domainToName(domain),
          path:        'B',
          source:      'semrush',
          context:     `Advertising on "${phrase}" (position ${row.Position}, CPC ~$${row['CPC (USD)']})`,
        });
      }

      // Avoid rate limits
      await sleep(300);
    } catch (err) {
      logger.warn(`SEMrush query failed for "${phrase}"`, { message: err.message });
    }
  }

  logger.info(`SEMrush: found ${results.length} PI advertisers in Ontario/GTA`);
  return results;
}

function parseSemrushCSV(raw) {
  if (!raw || !raw.includes(';')) return [];
  const lines   = raw.trim().split('\n');
  const headers = lines[0].split(';');
  return lines.slice(1).map(line => {
    const vals = line.split(';');
    return Object.fromEntries(headers.map((h, i) => [h, vals[i] || '']));
  });
}

function guessFirmEmail(domain) {
  return `info@${domain}`;
}

function domainToName(domain) {
  return domain
    .replace(/\.(ca|com|org|net|law)$/i, '')
    .replace(/[-_]/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

module.exports = { findPIAdvertisers };
