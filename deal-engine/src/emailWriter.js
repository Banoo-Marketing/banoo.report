'use strict'

const SUBJECTS = [
  'Cases are being lost after intake—not before it',
  'Question about your unretained files',
  'Do you re-engage closed consultations?',
  'Advertising isn\'t the problem',
  'Curious how your firm handles old leads',
  'Former leads are hiring other firms',
  'Most PI firms underestimate this revenue leak',
  'Are old inquiries still being contacted?',
  'What firms are doing with dormant leads in 2026',
]

let subjectIndex = 0

function buildEmail(prospect) {
  const firstName = prospect.firstName || null
  const greeting = firstName ? `Hey ${firstName},` : 'Hey,'

  const subject = SUBJECTS[subjectIndex % SUBJECTS.length]
  subjectIndex++

  const body = `${greeting}

Most PI firms have more signed-case potential sitting in old CRM contacts than in their current ad spend.

Are you re-engaging injury inquiries from the last 12–24 months?

Happy to share what GTA firms are doing to recover those cases.

---
Growth Plan for you:
PPC, SEO, Email Marketing, Social Media, Lead Generation, CRM Cleanup.

Banoo Legal Marketing
🇨🇦+1 (416) 400-4699`

  return { subject, body }
}

async function generateEmail(prospect) {
  return buildEmail(prospect)
}

module.exports = { generateEmail }
