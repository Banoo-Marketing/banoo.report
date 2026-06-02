const axios = require('axios');

const APOLLO_BASE = 'https://api.apollo.io/v1';

// Target cities across provinces
const TARGET_LOCATIONS = [
  // Ontario
  'Toronto, Ontario, Canada',
  'Ottawa, Ontario, Canada',
  'Hamilton, Ontario, Canada',
  'Mississauga, Ontario, Canada',
  'Brampton, Ontario, Canada',
  // Alberta
  'Calgary, Alberta, Canada',
  'Edmonton, Alberta, Canada',
  // British Columbia
  'Vancouver, British Columbia, Canada',
  'Surrey, British Columbia, Canada',
  'Burnaby, British Columbia, Canada',
  // Nova Scotia / Atlantic
  'Halifax, Nova Scotia, Canada',
  'Dartmouth, Nova Scotia, Canada',
];

const TARGET_TITLES = [
  // Family law
  'Family Lawyer',
  'Family Law Lawyer',
  'Divorce Lawyer',
  'Family Law Partner',
  // Litigation
  'Litigation Lawyer',
  'Civil Litigation Lawyer',
  'Commercial Litigation Lawyer',
  'Litigation Partner',
  'Trial Lawyer',
  // General
  'Managing Partner',
  'Founding Partner',
  'Principal Lawyer',
  'Barrister and Solicitor',
];

const EXCLUDE_FIRMS = [
  'fasken', 'mccarthy', 'blakes', 'blake cassels', 'osler', 'stikeman',
  'borden ladner', 'blg', 'norton rose', 'dentons', 'gowling',
  'diamond and diamond', 'preszler', 'fosters law',
];

async function findLawyers(count = 10, logger) {
  const key = process.env.APOLLO_API_KEY;
  if (!key) {
    logger.warn('APOLLO_API_KEY not set — skipping Apollo discovery');
    return [];
  }

  const results  = [];
  const seenEmails = new Set();

  logger.info('Apollo: searching family law + litigation lawyers across Canada');

  for (const location of TARGET_LOCATIONS) {
    if (results.length >= count) break;

    try {
      const payload = {
        api_key:          key,
        q_keywords:       'family law litigation',
        person_titles:    TARGET_TITLES,
        person_locations: [location],
        contact_email_status: ['verified', 'likely to engage', 'guessed'],
        organization_num_employees_ranges: ['1,30'],
        page:     1,
        per_page: 10,
      };

      const res = await axios.post(`${APOLLO_BASE}/mixed_people/search`, payload, {
        headers: { 'Content-Type': 'application/json', 'X-Api-Key': key, 'Cache-Control': 'no-cache' },
        timeout: 10000,
      });

      const people = res.data?.people || [];
      logger.info(`Apollo ${location}: ${people.length} results`);

      for (const person of people) {
        if (results.length >= count) break;

        const email = person.email;
        const org   = person.organization || {};
        const firm  = (org.name || '').toLowerCase();

        if (!email)                                        continue;
        if (seenEmails.has(email))                        continue;
        if (EXCLUDE_FIRMS.some(f => firm.includes(f)))    continue;

        seenEmails.add(email);

        const name    = [person.first_name, person.last_name].filter(Boolean).join(' ') || 'there';
        const orgName = org.name || '';
        const empSize = org.estimated_num_employees;
        const prov    = location.split(',')[1]?.trim() || '';

        results.push({
          name,
          first_name: person.first_name || null,
          email,
          firm:    orgName,
          title:   person.title || '',
          domain:  org.website_url || '',
          city:    person.city || location.split(',')[0],
          province: prov,
          size:    empSize ? `${empSize}-person firm` : 'boutique',
          path:    'B',
          source:  'apollo',
          context: `${person.title || 'Lawyer'} at ${orgName} — ${person.city || location.split(',')[0]}, ${prov}`,
        });
      }

      await sleep(400);
    } catch (err) {
      const status = err.response?.status;
      const msg    = err.response?.data?.message || err.message;

      if (status === 403 && String(msg).includes('allowlist')) {
        logger.warn('Apollo: IP not in allowlist. Whitelist at: apollo.io → Settings → API Keys');
        break;
      }
      if (status === 401) {
        logger.error('Apollo API key invalid');
        break;
      }
      logger.warn(`Apollo failed for ${location}`, { status, message: msg });
    }
  }

  logger.info(`Apollo: found ${results.length} prospects`);
  return results;
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

module.exports = { findLawyers };
