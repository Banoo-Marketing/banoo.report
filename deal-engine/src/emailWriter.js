'use strict'

const SUBJECTS = [
  'Quick question about your old PI files',
  'Are former leads hiring other firms?',
  'Do you follow up on unsigned retainers?',
  'Most PI firms miss this revenue source',
  'Old injury inquiries — what happens to them?',
  'What GTA firms are doing with dormant leads',
]

let subjectIndex = 0

function buildEmail(prospect) {
  const firstName = prospect.firstName || null
  const greeting = firstName ? `Hi ${firstName},` : 'Hi there,'

  const subject = SUBJECTS[subjectIndex % SUBJECTS.length]
  subjectIndex++

  const body = `${greeting}

Most PI firms have more signed-case potential sitting in old CRM contacts than in their current ad spend.

Are you re-engaging injury inquiries from the last 12–24 months?

Happy to share what GTA firms are doing to recover those cases.

Emod Vafa
Banoo Marketing
banoo.marketing
+1 (416) 400-4699
cal.com/emodvafa`

  return { subject, body }
}

async function generateEmail(prospect) {
  return buildEmail(prospect)
}

module.exports = { generateEmail }
