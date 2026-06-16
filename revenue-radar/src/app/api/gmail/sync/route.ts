import { NextRequest, NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'
import { getAuthClient, fetchThreads, fetchThreadDetails, fetchIncrementalChanges, getGmailProfile } from '@/lib/gmail'
import { classifyEmail } from '@/lib/email-filter'
import { detectOpportunity } from '@/agents/opportunity-detector'
import { detectMissedFollowup } from '@/agents/missed-followup-detector'
import { detectChurnRisk } from '@/agents/churn-detector'
import { generateReactivation } from '@/agents/reactivation-engine'

export async function POST(req: NextRequest) {
  const { session, error } = await requireSession()
  if (error) return error

  const userId = session!.user!.id!
  const userEmail = session!.user!.email!

  const gmailToken = await prisma.gmailToken.findUnique({ where: { userId } })
  if (!gmailToken) {
    return NextResponse.json({ error: 'Gmail not connected' }, { status: 400 })
  }

  const auth = getAuthClient(gmailToken.accessToken, gmailToken.refreshToken)
  let threadIds: string[] = []
  let newHistoryId = gmailToken.lastHistoryId ?? ''

  try {
    if (gmailToken.lastHistoryId) {
      const changes = await fetchIncrementalChanges(auth, gmailToken.lastHistoryId)
      threadIds = changes.threadIds
      newHistoryId = changes.newHistoryId
    } else {
      const profile = await getGmailProfile(auth)
      newHistoryId = profile.historyId

      const { threads } = await fetchThreads(auth, { maxResults: 100 })
      threadIds = threads.map(t => t.id)
    }

    await prisma.gmailToken.update({
      where: { userId },
      data: { lastHistoryId: newHistoryId, lastSyncAt: new Date() },
    })

    let processed = 0
    let opportunities = 0
    let churnRisks = 0
    let followUps = 0
    let reactivations = 0

    for (const threadId of threadIds.slice(0, 50)) {
      try {
        const threadDetails = await fetchThreadDetails(auth, threadId)
        if (!threadDetails) continue

        const classification = classifyEmail(threadDetails)

        const thread = await prisma.emailThread.upsert({
          where: { userId_gmailThreadId: { userId, gmailThreadId: threadId } },
          update: {
            subject: threadDetails.subject,
            snippet: threadDetails.snippet,
            participants: threadDetails.participants,
            lastMessageAt: threadDetails.lastMessageAt,
            isHumanConversation: classification.isHuman,
          },
          create: {
            userId,
            gmailThreadId: threadId,
            subject: threadDetails.subject,
            snippet: threadDetails.snippet,
            participants: threadDetails.participants,
            lastMessageAt: threadDetails.lastMessageAt,
            isHumanConversation: classification.isHuman,
          },
        })

        for (const msg of threadDetails.messages) {
          await prisma.emailMessage.upsert({
            where: { threadId_gmailMessageId: { threadId: thread.id, gmailMessageId: msg.gmailMessageId } },
            update: {},
            create: {
              threadId: thread.id,
              gmailMessageId: msg.gmailMessageId,
              from: msg.from,
              to: msg.to,
              subject: msg.subject,
              bodyText: msg.bodyText,
              sentAt: msg.sentAt,
            },
          })
        }

        if (!classification.isHuman) continue
        if (thread.isProcessed) continue

        const [opportunity, churn, followUp, reactivation] = await Promise.allSettled([
          detectOpportunity(threadDetails, userEmail),
          detectChurnRisk(threadDetails, userEmail),
          detectMissedFollowup(threadDetails, userEmail),
          generateReactivation(threadDetails, userEmail),
        ])

        if (opportunity.status === 'fulfilled' && opportunity.value) {
          const o = opportunity.value
          await prisma.opportunitySignal.create({
            data: {
              userId,
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
          opportunities++
        }

        if (churn.status === 'fulfilled' && churn.value) {
          const c = churn.value
          await prisma.churnSignal.create({
            data: {
              userId,
              threadId: thread.id,
              client: c.client,
              churnScore: c.churn_score,
              riskLevel: c.risk_level,
              reasons: c.reasons,
              recommendedAction: c.recommended_action,
            },
          })
          churnRisks++
        }

        if (followUp.status === 'fulfilled' && followUp.value) {
          followUps++
        }

        if (reactivation.status === 'fulfilled' && reactivation.value) {
          const r = reactivation.value
          await prisma.reactivationContact.upsert({
            where: { id: `${userId}-${r.email}` },
            update: {
              reactivationReason: r.reactivation_reason,
              recommendedOffer: r.recommended_offer,
              emailDraft: r.email_draft,
            },
            create: {
              userId,
              email: r.email,
              name: r.contact,
              company: r.company,
              lastContactDate: new Date(r.last_contact_date),
              reactivationReason: r.reactivation_reason,
              recommendedOffer: r.recommended_offer,
              emailDraft: r.email_draft,
            },
          })
          reactivations++
        }

        await prisma.emailThread.update({
          where: { id: thread.id },
          data: { isProcessed: true },
        })

        processed++
      } catch (err) {
        console.error(`Error processing thread ${threadId}:`, err)
      }
    }

    return NextResponse.json({
      success: true,
      processed,
      opportunities,
      churnRisks,
      followUps,
      reactivations,
    })
  } catch (err) {
    console.error('Sync error:', err)
    return NextResponse.json({ error: 'Sync failed' }, { status: 500 })
  }
}
