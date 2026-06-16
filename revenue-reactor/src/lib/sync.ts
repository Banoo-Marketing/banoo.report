import { prisma } from './db'
import { getAuthClient, listThreadIds, getIncrementalThreadIds, getThread } from './gmail'
import { isHumanConversation } from './email-filter'
import { findOpportunity } from '@/agents/opportunity-finder'
import { detectChurn } from '@/agents/churn-detector'
import { adviseRetention } from '@/agents/retention-advisor'
import { findReactivation } from '@/agents/reactivation-finder'

export interface SyncResult {
  processed: number
  opportunities: number
  churnSignals: number
  retentionInsights: number
  reactivations: number
  threadsAnalyzed: number
  emailsAnalyzed: number
}

export function interpretSyncError(err: unknown): string {
  const msg = err instanceof Error ? err.message : String(err)
  if (msg.includes('invalid_grant') || msg.includes('Token has been expired') || msg.includes('401'))
    return 'Google connection expired. Please reconnect Gmail.'
  if (msg.includes('ECONNREFUSED') || msg.includes('ETIMEDOUT') || msg.includes('network'))
    return 'Could not connect to Google. Check your internet connection.'
  if (msg.includes('rateLimitExceeded') || msg.includes('429'))
    return 'Too many requests to Gmail. Will retry automatically in a few minutes.'
  if (msg.includes('No Gmail token'))
    return 'Gmail is not connected. Please connect your Gmail account.'
  return 'Something went wrong during sync. Please try again.'
}

export async function syncUser(userId: string, userEmail: string): Promise<SyncResult> {
  const token = await prisma.gmailToken.findUnique({ where: { userId } })
  if (!token) throw new Error('No Gmail token')

  const auth = getAuthClient(token.accessToken, token.refreshToken)
  let threadIds: string[]
  let newHistoryId: string

  if (token.lastHistoryId) {
    const inc = await getIncrementalThreadIds(auth, token.lastHistoryId)
    threadIds = inc.ids
    newHistoryId = inc.historyId
  } else {
    const full = await listThreadIds(auth, 100)
    threadIds = full.ids
    newHistoryId = full.historyId
  }

  const result: SyncResult = {
    processed: 0, opportunities: 0, churnSignals: 0,
    retentionInsights: 0, reactivations: 0,
    threadsAnalyzed: 0, emailsAnalyzed: 0,
  }

  const batch = threadIds.slice(0, 50)
  result.threadsAnalyzed = batch.length

  for (const tid of batch) {
    try {
      const threadData = await getThread(auth, tid)
      if (!threadData) continue

      result.emailsAnalyzed += threadData.messages.length

      const isHuman = isHumanConversation(threadData)

      const thread = await prisma.emailThread.upsert({
        where: { userId_gmailThreadId: { userId, gmailThreadId: tid } },
        update: { subject: threadData.subject, snippet: threadData.snippet, participants: threadData.participants, lastMessageAt: threadData.lastMessageAt, isHumanConversation: isHuman },
        create: { userId, gmailThreadId: tid, subject: threadData.subject, snippet: threadData.snippet, participants: threadData.participants, lastMessageAt: threadData.lastMessageAt, isHumanConversation: isHuman },
      })

      for (const msg of threadData.messages) {
        await prisma.emailMessage.upsert({
          where: { threadId_gmailMessageId: { threadId: thread.id, gmailMessageId: msg.gmailMessageId } },
          update: {},
          create: { threadId: thread.id, gmailMessageId: msg.gmailMessageId, from: msg.from, to: msg.to, subject: msg.subject, bodyText: msg.bodyText, sentAt: msg.sentAt },
        })
      }

      if (!isHuman || thread.isProcessed) continue

      const [opp, churn, retention, reactivation] = await Promise.allSettled([
        findOpportunity(threadData, userEmail),
        detectChurn(threadData, userEmail),
        adviseRetention(threadData, userEmail),
        findReactivation(threadData, userEmail),
      ])

      if (opp.status === 'fulfilled' && opp.value) {
        const o = opp.value
        await prisma.opportunity.create({ data: { userId, threadId: thread.id, contactName: o.contactName, company: o.company, opportunityScore: o.opportunityScore, revenueConfidence: o.revenueConfidence, estimatedValue: o.estimatedValue, reason: o.reason, evidence: o.evidence, suggestedAction: o.suggestedAction } })
        result.opportunities++
      }

      if (churn.status === 'fulfilled' && churn.value) {
        const c = churn.value
        await prisma.churnSignal.create({ data: { userId, threadId: thread.id, clientName: c.clientName, churnScore: c.churnScore, riskLevel: c.riskLevel, reasons: c.reasons, whatHappened: c.whatHappened, whyItMatters: c.whyItMatters, recommendedAction: c.recommendedAction } })
        result.churnSignals++
      }

      if (retention.status === 'fulfilled' && retention.value) {
        const r = retention.value
        await prisma.retentionInsight.create({ data: { userId, threadId: thread.id, clientName: r.clientName, insight: r.insight, suggestedMessage: r.suggestedMessage, timing: r.timing } })
        result.retentionInsights++
      }

      if (reactivation.status === 'fulfilled' && reactivation.value) {
        const rv = reactivation.value
        const existing = await prisma.reactivationTarget.findFirst({ where: { userId, email: rv.email } })
        if (!existing) {
          await prisma.reactivationTarget.create({ data: { userId, email: rv.email, contactName: rv.contactName, company: rv.company, lastContactDate: new Date(rv.lastContactDate), history: rv.history, whyContact: rv.whyContact, suggestedOffer: rv.suggestedOffer, suggestedMessage: rv.suggestedMessage } })
          result.reactivations++
        }
      }

      await prisma.emailThread.update({ where: { id: thread.id }, data: { isProcessed: true } })
      result.processed++
    } catch (err) {
      console.error(`Thread ${tid} error:`, err)
    }
  }

  await prisma.gmailToken.update({
    where: { userId },
    data: {
      lastHistoryId: newHistoryId,
      lastSyncAt: new Date(),
      lastSyncError: null,
      threadsAnalyzed: { increment: result.threadsAnalyzed },
      emailsAnalyzed: { increment: result.emailsAnalyzed },
    },
  })

  return result
}
