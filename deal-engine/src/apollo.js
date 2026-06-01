const axios = require('axios');

const APOLLO_BASE = 'https://api.apollo.io/v1';

const ONTARIO_LOCATIONS = [
  'Toronto, Ontario, Canada',
  'Mississauga, Ontario, Canada',
  'Brampton, Ontario, Canada',
  'Hamilton, Ontario, Canada',
  'Ottawa, Ontario, Canada',
  'Oakville, Ontario, Canada',
  'Markham, Ontario, Canada',
  'North York, Ontario, Canada',
];

const PI_TITLES = [
  'Personal Injury Lawyer',
  'Injury Lawyer',
  'Personal Injury Attorney',
  'Barrister',
  'Barrister and Solicitor',
  'Managing Partner',
  'Founding Partner',
  'Principal Lawyer',
  'Partner',
];

// Firms already contacted or in pipeline — skip these
const EXCLUDE_FIRMS = [
  'diamond and diamond',
  'preszler',
  'fosters law',
  'grillo law',
  'schiffmann',
  'sokoloff',
  'longo lawyers',
  'karapancev',
  'kain & ball',
  'kain ball',
];

async function findPILawyers(count = 10, logger) {
  const key = process.env.APOLLO_API_KEY;
  if (!key) {
    logger.warn('APOLLO_API_KEY not set — skipping Apollo discovery');
    return [];
  }

  const results = [];
  const seenEmails = new Set();

  logger.info('Apollo: searching for PI lawyers in Ontario/GTA');

  for (const location of ONTARIO_LOCATIONS) {
    if (results.length >= count) break;

    try {
      const payload = {
        api_key:              key,
        q_keywords:           'personal injury law',
        person_titles:        PI_TITLES,
        person_locations:     [location],
        contact_email_status: ['verified', 'likely to engage', 'guessed'],
        organization_num_employees_ranges: ['1,20'],
        page:                 1,
        per_page:             10,
      };

      const res = await axios.post(`${APOLLO_BASE}/mixed_people/search`, payload, {
        headers: {
          'Content-Type': 'application/json',
          'X-Api-Key':    key,
          'Cache-Control': 'no-cache',
        },
        timeout: 10000,
      });

      const people = res.data?.people || [];
      logger.info(`Apollo ${location}: ${people.length} results`);

      for (const person of people) {
        if (results.length >= count) break;

        const email = person.email;
        const org   = person.organization || {};
        const firm  = (org.name || '').toLowerCase();

        // Skip if no email, already seen, or in excluded list
        if (!email)                                   continue;
        if (seenEmails.has(email))                    continue;
        if (EXCLUDE_FIRMS.some(f => firm.includes(f))) continue;

        seenEmails.add(email);

        const name    = [person.first_name, person.last_name].filter(Boolean).join(' ') || 'there';
        const orgName = org.name || domainToName(person.organization_name || '');
        const empSize = org.estimated_num_employees;
        const sizeStr = empSize ? `${empSize}-person firm` : 'boutique firm';

        results.push({
          name,
          first_name: person.first_name || name,
          email,
          firm:    orgName,
          title:   person.title || '',
          domain:  org.website_url || '',
          city:    person.city || location.split(',')[0],
          size:    sizeStr,
          path:    'B',
          source:  'apollo',
          context: `${person.title || 'PI lawyer'} at ${orgName} — ${sizeStr} in ${person.city || location.split(',')[0]}`,
          keyword: 'personal injury lawyer ontario',
        });
      }

      await sleep(400);
    } catch (err) {
      const status = err.response?.status;
      const msg    = err.response?.data?.message || err.message;
      logger.warn(`Apollo search failed for ${location}`, { status, message: msg });
      if (status === 403 && msg?.includes('allowlist')) {
        logger.warn('Apollo: IP not in allowlist. Add your server IP at: apollo.io → Settings → API Keys');
        break;
      }
      if (status === 401) {
        logger.error('Apollo API key invalid — check APOLLO_API_KEY in .env');
        break;
      }
    }
  }

  logger.info(`Apollo: found ${results.length} PI lawyer prospects with emails`);
  return results;
}

async function enrichContact(email, logger) {
  const key = process.env.APOLLO_API_KEY;
  if (!key) return null;

  try {
    const res = await axios.post(`${APOLLO_BASE}/people/match`, {
      api_key: key,
      email,
      reveal_personal_emails: false,
    }, {
      headers: { 'Content-Type': 'application/json', 'X-Api-Key': key },
      timeout: 8000,
    });

    const p = res.data?.person;
    if (!p) return null;

    return {
      name:       [p.first_name, p.last_name].filter(Boolean).join(' '),
      first_name: p.first_name,
      title:      p.title,
      firm:       p.organization?.name,
      linkedin:   p.linkedin_url,
      city:       p.city,
    };
  } catch (_) {
    return null;
  }
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

module.exports = { findPILawyers, enrichContact };
