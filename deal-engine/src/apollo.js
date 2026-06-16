'use strict'
const axios = require('axios')
const { log } = require('./logger')

const BASE = 'https://api.apollo.io/api/v1'

async function searchPILawyers(page = 1) {
  try {
    const res = await axios.post(
      `${BASE}/mixed_people/search`,
      {
        api_key: process.env.APOLLO_API_KEY,
        q_keywords: 'personal injury lawyer',
        person_titles: ['partner', 'founder', 'managing partner', 'principal', 'lawyer', 'attorney'],
        person_locations: [
          'Toronto, Ontario, Canada',
          'Mississauga, Ontario, Canada',
          'Brampton, Ontario, Canada',
          'Hamilton, Ontario, Canada',
          'Ottawa, Ontario, Canada',
        ],
        organization_num_employees_ranges: ['1,20'],
        page,
        per_page: 10,
      },
      {
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': process.env.APOLLO_API_KEY,
        },
        timeout: 15000,
      }
    )
    return (res.data.people || []).map(p => ({
      name: p.name,
      email: p.email,
      company: p.organization?.name,
      title: p.title,
      city: p.city,
      pathType: 'cold',
    }))
  } catch (err) {
    log('Apollo search failed: ' + (err.response?.data?.error || err.message))
    return []
  }
}

module.exports = { searchPILawyers }
