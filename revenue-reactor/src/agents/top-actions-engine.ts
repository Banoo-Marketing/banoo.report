import type { BoardOpportunity, BoardChurnSignal, BoardReactivationTarget, TopAction } from '@/types'

const TODAY_CUTOFF = 75
const TODAY_MAX = 5

function urgencyScore(daysOld: number): number {
  if (daysOld <= 2) return 100
  if (daysOld <= 7) return 75
  if (daysOld <= 14) return 50
  if (daysOld <= 30) return 25
  return 10
}

function evidenceScore(count: number): number {
  if (count === 0) return 0
  if (count === 1) return 40
  if (count === 2) return 70
  return 90
}

function reactivationWindow(daysSinceContact: number): number {
  if (daysSinceContact >= 60 && daysSinceContact <= 120) return 80
  if (daysSinceContact >= 30 && daysSinceContact < 60) return 60
  if (daysSinceContact > 120 && daysSinceContact <= 180) return 55
  return 35
}

// Priority = (Revenue Potential × 0.4) + (Urgency × 0.3) + (Evidence Strength × 0.2) + (Recency × 0.1)
function prioritize(rp: number, urgency: number, evidence: number, recency: number): number {
  return Math.round(rp * 0.4 + urgency * 0.3 + evidence * 0.2 + recency * 0.1)
}

export function buildTopActions(
  opportunities: BoardOpportunity[],
  churnSignals: BoardChurnSignal[],
  reactivationTargets: BoardReactivationTarget[],
  limit = TODAY_MAX,
  notUsefulIds: Set<string> = new Set()
): TopAction[] {
  const actions: TopAction[] = []

  for (const op of opportunities) {
    if (notUsefulIds.has(op.id)) continue
    const daysOld = Math.floor((Date.now() - new Date(op.createdAt).getTime()) / 86400000)
    const rp = op.revenueConfidence ?? op.opportunityScore
    const urgency = urgencyScore(daysOld)
    const es = evidenceScore(op.evidence.length)
    const score = prioritize(rp, urgency, es, urgency)
    if (score < TODAY_CUTOFF) continue
    actions.push({
      id: op.id,
      type: 'opportunity',
      name: op.contactName,
      company: op.company,
      priorityScore: score,
      revenueConfidence: op.revenueConfidence,
      estimatedValue: op.estimatedValue,
      reason: op.reason,
      action: op.suggestedAction,
    })
  }

  for (const c of churnSignals) {
    if (notUsefulIds.has(c.id)) continue
    const daysOld = Math.floor((Date.now() - new Date(c.createdAt).getTime()) / 86400000)
    const rp = c.churnScore
    const urgency = c.riskLevel === 'high' ? 100 : c.riskLevel === 'medium' ? 60 : 20
    const es = evidenceScore(c.reasons.length)
    const recency = urgencyScore(daysOld)
    const score = prioritize(rp, urgency, es, recency)
    if (score < TODAY_CUTOFF) continue
    actions.push({
      id: c.id,
      type: 'churn',
      name: c.clientName,
      company: null,
      priorityScore: score,
      revenueConfidence: null,
      estimatedValue: null,
      reason: c.whatHappened ?? c.reasons[0] ?? '',
      action: c.recommendedAction,
      riskLevel: c.riskLevel,
    })
  }

  for (const rv of reactivationTargets) {
    if (notUsefulIds.has(rv.id)) continue
    const daysSinceContact = Math.floor((Date.now() - new Date(rv.lastContactDate).getTime()) / 86400000)
    const daysOld = Math.floor((Date.now() - new Date(rv.lastContactDate).getTime()) / 86400000)
    const rp = reactivationWindow(daysSinceContact)
    const urgency = rp
    const es = rv.whyContact ? 80 : 30
    const recency = urgencyScore(daysOld)
    const score = prioritize(rp, urgency, es, recency)
    if (score < TODAY_CUTOFF) continue
    actions.push({
      id: rv.id,
      type: 'reactivation',
      name: rv.contactName,
      company: rv.company,
      priorityScore: score,
      revenueConfidence: null,
      estimatedValue: null,
      reason: rv.whyContact ?? rv.history,
      action: rv.suggestedOffer,
      email: rv.email,
    })
  }

  return actions.sort((a, b) => b.priorityScore - a.priorityScore).slice(0, limit)
}
