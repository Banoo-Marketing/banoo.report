const axios = require('axios');

const SEMRUSH_BASE = 'https://api.semrush.com/';

const TARGET_PHRASES = [
  // Calgary
  'family lawyer calgary',
  'divorce lawyer calgary',
  'litigation lawyer calgary',
  'civil litigation calgary',
  // BC
  'family lawyer vancouver',
  'divorce lawyer vancouver',
  'litigation lawyer vancouver',
  'family lawyer surrey bc',
  'family lawyer victoria bc',
];

const EXCLUDE_DOMAINS = [
  'fasken.com', 'mccarthy.ca', 'blakes.com', 'osler.com', 'stikeman.com',
  'bdplaw.com', 'gowlingwlg.com', 'nortonrosefulbright.com', 'dentons.com',
  'diamondlaw.ca', 'preszlerlaw.ca',
];

async function findAdvertisers(logger) {
  const key = process.env.SEMRUSH_API_KEY;
  if (!key) {
    logger.warn('SEMRUSH_API_KEY not set — skipping SEMrush');
    return [];
  }

  const results = [];
  const seen    = new Set(EXCLUDE_DOMAINS);

  for (const phrase of TARGET_PHRASES) {
    if (results.length >= 12) break;

    try {
      const params = new URLSearchParams({
        type:           'phrase_adwords',
        key,
        phrase,
        database:       'ca',
        export_columns: 'Dn,Po,Tr,Cp,Co',
        display_limit:  '8',
        display_sort:   'tr_desc',
      });

      const res  = await axios.get(`${SEMRUSH_BASE}?${params}`);
      const rows = parseSemrushCSV(res.data);

      for (const row of rows) {
        const domain = (row.Domain || '').toLowerCase().trim();
        if (!domain || seen.has(domain)) continue;
        seen.add(domain);

        const province = inferProvince(phrase);
        results.push({
          domain,
          email:    `info@${domain}`,
          name:     domainToName(domain),
          firm:     domainToName(domain),
          city:     inferCity(phrase),
          province,
          path:     'B',
          source:   'semrush',
          context:  `Advertising on "${phrase}" in Canada (CPC ~$${row['CPC (USD)']})`,
          keyword:  phrase,
        });
      }

      await sleep(300);
    } catch (err) {
      const msg = err.response?.data || err.message;
      if (String(msg).includes('allowlist')) {
        logger.warn('SEMrush: IP not in allowlist. Whitelist at: semrush.com → Subscription → API');
        break;
      }
      logger.warn(`SEMrush failed for "${phrase}"`, { message: err.message });
    }
  }

  logger.info(`SEMrush: found ${results.length} advertisers`);
  return results;
}

function inferProvince(phrase) {
  if (/calgary/.test(phrase)) return 'Alberta';
  return 'British Columbia';
}

function inferCity(phrase) {
  const map = {
    calgary: 'Calgary', vancouver: 'Vancouver', surrey: 'Surrey', victoria: 'Victoria',
  };
  for (const [k, v] of Object.entries(map)) {
    if (phrase.includes(k)) return v;
  }
  return 'Vancouver';
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

function domainToName(domain) {
  return domain
    .replace(/\.(ca|com|org|net|law)$/i, '')
    .replace(/[-_]/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

module.exports = { findAdvertisers };
