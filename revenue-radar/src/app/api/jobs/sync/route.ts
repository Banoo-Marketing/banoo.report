import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/db'
import { getAuthClient, fetchThreads, fetchThreadDetails, fetchIncrementalChanges, getGmailProfile } from '@/lib/gmail'
import { classifyEmail } from '@/lib/email-filter'
import { detectOpportunity } from '@/agents/opportunity-detector'
import { detectMissedFollowup } from '@/agents/missed-followup-detector'
import { detectChurnRisk } from '@/agents/churn-detector'
import { generateReactivation } from '@/agents/reactivation-engine'

export async function GET(req: NextRequest) {
  const secret = req.headers.get('authorization')?.replace('Bearer ', '')
  if (secret !== process.env.CRON_SECRET) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const users = await prisma.user.findMany({
    include: { gmailToken: true },
  })

  const results = []

  for (const user of users) {
    if (!user.gmailToken) continue

    const token = user.gmailToken
    const auth = getAuthClient(token.accessToken, token.refreshToken)
    const userEmail = user.email

    try {
      let threadIds: string[] = []
      let newHistoryId = token.lastHistoryId ?? ''

      if (token.lastHistoryId) {
        const changes = await fetchIncrementalChanges(auth, token.lastHistoryId)
        threadIds = changes.threadIds
        newHistoryId = changes.newHistoryId
      } else {
        const profile = await getGmailProfile(auth)
        newHistoryId = profile.historyId
        const { threads } = await fetchThreads(auth, { maxResults: 50 })
        threadIds = threads.map(t => t.id)
      }

      await prisma.gmailToken.update({
        where: { userId: user.id },
        data: { lastHistoryId: newHistoryId, lastSyncAt: new Date() },
      })

      let processed = 0

      for (const threadId of threadIds.slice(0, 20)) {
        try {
          const threadDetails = await fetchThreadDetails(auth, threadId)
          if (!threadDetails) continue

          const classification = classifyEmail(threadDetails)

          const thread = await prisma.emailThread.upsert({
            where: { userId_gmailThreadId: { userId: user.id, gmailThreadId: threadId } },
            update: {
              subject: threadDetails.subject,
              snippet: threadDetails.snippet,
              participants: threadDetails.participants,
              lastMessageAt: threadDetails.lastMessageAt,
              isHumanConversation: classification.isHuman,
            },
            create: {
              userId: user.id,
              gmailThreadId: threadId,
              subject: threadDetails.subject,
              snippet: threadDetails.snippet,
              participants: threadDetails.participants,
              lastMessageAt: threadDetails.lastMessageAt,
              isHumanConversation: classification.isHuman,
            },
          })

          if (!classification.isHuman || thread.isProcessed) continue

          await Promise.allSettled([
            detectOpportunity(threadDetails, userEmail).then(async o => {
              if (!o) return
              await prisma.opportunitySignal.create({
                data: {
                  userId: user.id,
                  threadId: thread.id,
                  contactName: o.contact_name,
                  company: o.company,
                  opportunityScore: o.opportunity_score,
                  estimatedValue: o.estimated_value,
                  reason: o.reason,
                  evidence: o.evidence,
                  recommendedAction: o.recommended_action,
                },
              })
            }),
            detectChurnRisk(threadDetails, userEmail).then(async c => {
              if (!c) return
              await prisma.churnSignal.create({
                data: {
                  userId: user.id,
                  threadId: thread.id,
                  client: c.client,
                  churnScore: c.churn_score,
                  riskLevel: c.risk_level,
                  reasons: c.reasons,
                  recommendedAction: c.recommended_action,
                },
              })
            }),
            detectMissedFollowup(threadDetails, userEmail),
            generateReactivation(threadDetails, userEmail).then(async r => {
              if (!r) return
              await prisma.reactivationContact.upsert({
                where: { id: `${user.id}-${r.email}` },
                update: {
                  reactivationReason: r.reactivation_reason,
                  recommendedOffer: r.recommended_offer,
                  emailDraft: r.email_draft,
                },
                create: {
                  userId: user.id,
                  email: r.email,
                  name: r.contact,
                  company: r.company,
                  lastContactDate: new Date(r.last_contact_date),
                  reactivationReason: r.reactivation_reason,
                  recommendedOffer: r.recommended_offer,
                  emailDraft: r.email_draft,
                },
              })
            }),
          ])

          await prisma.emailThread.update({
            where: { id: thread.id },
            data: { isProcessed: true },
          })

          processed++
        } catch (err) {
          console.error(`Error processing thread ${threadId}:`, err)
        }
      }

      results.push({ userId: user.id, processed, status: 'ok' })
    } catch (err) {
      console.error(`Sync failed for user ${user.id}:`, err)
      results.push({ userId: user.id, status: 'error' })
    }
  }

  return NextResponse.json({ synced: results.length, results })
}
