import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  console.log('Seeding demo data...')

  const user = await prisma.user.upsert({
    where: { email: 'demo@example.com' },
    update: {},
    create: {
      email: 'demo@example.com',
      name: 'Demo User',
    },
  })

  console.log(`User: ${user.email}`)

  // Opportunities
  await prisma.opportunitySignal.createMany({
    data: [
      {
        userId: user.id,
        contactName: 'Sarah Mitchell',
        company: 'Apex Roofing Co.',
        opportunityScore: 87,
        estimatedValue: '$12,000',
        reason: 'Client asked for a detailed proposal on a commercial roof replacement project. Budget pre-approved.',
        evidence: ['Requested formal quote', 'Mentioned Q1 budget availability', 'Asked for timeline'],
        recommendedAction: 'Send detailed proposal within 48 hours with competitive pricing and timeline.',
      },
      {
        userId: user.id,
        contactName: 'James Okonkwo',
        company: 'Okonkwo Law Firm',
        opportunityScore: 72,
        estimatedValue: '$4,500/month',
        reason: 'Law firm looking for ongoing SEO and digital marketing support.',
        evidence: ['Asked about SEO retainer pricing', 'Mentioned competitor dropped the ball', 'Ready to start ASAP'],
        recommendedAction: 'Schedule discovery call and prepare a tailored SEO roadmap.',
      },
      {
        userId: user.id,
        contactName: 'Emily Zhao',
        company: 'Zhao Real Estate Group',
        opportunityScore: 65,
        estimatedValue: '$8,000',
        reason: 'Real estate agency interested in website redesign and lead generation setup.',
        evidence: ['Asked for web design portfolio', 'Inquired about lead gen integrations'],
        recommendedAction: 'Send portfolio with real estate case studies and a 3-tier pricing proposal.',
      },
    ],
    skipDuplicates: true,
  })

  // Churn signals
  await prisma.churnSignal.createMany({
    data: [
      {
        userId: user.id,
        client: 'Bluestone Property Management',
        churnScore: 78,
        riskLevel: 'high',
        reasons: ['Complained about delayed deliverables twice', 'Mentioned looking at other agencies'],
        recommendedAction: 'Schedule urgent call within 24 hours. Offer a project review meeting.',
      },
      {
        userId: user.id,
        client: 'ClearView Windows & Doors',
        churnScore: 54,
        riskLevel: 'medium',
        reasons: ['Budget concerns mentioned', 'Replied less frequently this month'],
        recommendedAction: 'Send a value recap email highlighting results achieved.',
      },
    ],
    skipDuplicates: true,
  })

  // Reactivation contacts
  await prisma.reactivationContact.createMany({
    data: [
      {
        userId: user.id,
        email: 'carlos@rivera-landscaping.com',
        name: 'Carlos Rivera',
        company: 'Rivera Landscaping',
        lastContactDate: new Date(Date.now() - 92 * 24 * 60 * 60 * 1000),
        reactivationReason: 'Previous client who used website design services 3 months ago.',
        recommendedOffer: 'Spring marketing campaign package with Google Ads + social media',
        emailDraft: "Hi Carlos,\n\nI hope business is going well as spring approaches! I wanted to reach out about a spring marketing push to help drive more calls during peak season.\n\nWould you be open to a quick 15-minute call this week?\n\nBest,",
      },
      {
        userId: user.id,
        email: 'priya@nair-consulting.com',
        name: 'Priya Nair',
        company: 'Nair Business Consulting',
        lastContactDate: new Date(Date.now() - 145 * 24 * 60 * 60 * 1000),
        reactivationReason: 'Former client who completed a brand refresh project.',
        recommendedOffer: 'Q2 marketing strategy refresh + LinkedIn content package',
        emailDraft: "Hi Priya,\n\nIt's been a few months since we completed your brand refresh! I've been working on some new LinkedIn strategies that have been getting great results for consultants.\n\nThought of you and wanted to check if there's anything we can help with.\n\nWarm regards,",
      },
    ],
    skipDuplicates: true,
  })

  console.log('Seed complete!')
}

main()
  .catch(e => { console.error(e); process.exit(1) })
  .finally(() => prisma.$disconnect())
