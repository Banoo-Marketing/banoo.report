'use strict'

const SUBJECTS = [
  'Question about your unretained PI files',
  'Do you re-engage old injury consultations?',
  'Cases lost after intake — not before it',
  'Former leads are hiring other firms',
  'Are old inquiries still being contacted?',
  'What Ontario PI firms are doing differently in 2026',
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

Banoo Legal Marketing
🇨🇦+1 (416) 400-4699`

  return { subject, body }
}

async function generateEmail(prospect) {
  return buildEmail(prospect)
}

module.exports = { generateEmail }
