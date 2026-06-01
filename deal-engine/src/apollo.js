const axios = require('axios');

const APOLLO_BASE = 'https://api.apollo.io/v1';

const PI_KEYWORDS = ['personal injury', 'personal injury lawyer', 'PI law', 'accident lawyer', 'injury attorney'];

const GTA_CITIES = ['Toronto', 'Mississauga', 'Brampton', 'Hamilton', 'Ottawa', 'Scarborough', 'North York', 'Markham'];

/**
 * Search Apollo.io for PI lawyers in Ontario.
 * Returns prospects formatted for emailWriter.
 */
async function searchPILawyers(limit = 5) {
  const apiKey = process.env.APOLLO_API_KEY;
  if (!apiKey) {
    console.error('APOLLO_API_KEY not set');
    return [];
  }

  const payload = {
    api_key: apiKey,
    q_keywords: 'personal injury lawyer',
    person_titles: [
      'Personal Injury Lawyer',
      'Managing Partner',
      'Partner',
      'Attorney',
      'Principal Lawyer',
      'Founding Lawyer',
    ],
    person_locations: GTA_CITIES.map((c) => `${c}, Ontario, Canada`),
    organization_industry_tag_ids: [],
    per_page: limit * 3,
    page: 1,
  };

  let data;
  try {
    const res = await axios.post(`${APOLLO_BASE}/mixed_people/search`, payload, {
      headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache' },
      timeout: 15000,
    });
    data = res.data;
  } catch (err) {
    console.error('Apollo search error:', err.response?.data || err.message);
    return [];
  }

  const people = data?.people || [];
  const prospects = [];

  for (const p of people) {
    if (prospects.length >= limit) break;
    if (!p.email) continue;

    const firmName = p.organization?.name || '';
    const employeeCount = p.organization?.estimated_num_employees || 0;

    // Filter: solo to 20-person firms
    if (employeeCount > 20) continue;

    prospects.push({
      source: 'apollo',
      path: 'B',
      name: `${p.first_name || ''} ${p.last_name || ''}`.trim(),
      email: p.email,
      title: p.title || 'Lawyer',
      firmName,
      city: p.city || p.organization?.city || '',
      employeeCount,
      linkedinUrl: p.linkedin_url || '',
    });
  }

  return prospects;
}

module.exports = { searchPILawyers };
