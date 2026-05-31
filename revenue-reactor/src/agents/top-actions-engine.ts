import type { BoardOpportunity, BoardChurnSignal, BoardReactivationTarget, TopAction } from '@/types'

const TODAY_CUTOFF = 78
const TODAY_MAX = 3

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

// Final Priority Score = (Revenue Confidence × 0.5) + (Evidence Strength × 0.3) + (Urgency × 0.2)
function prioritize(confidence: number, evidence: number, urgency: number): number {
  return Math.round(confidence * 0.5 + evidence * 0.3 + urgency * 0.2)
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
    const confidence = op.revenueConfidence ?? op.opportunityScore
    const es = evidenceScore(op.evidence.length)
    const urgency = urgencyScore(daysOld)
    const score = prioritize(confidence, es, urgency)
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
    const confidence = c.churnScore
    const es = evidenceScore(c.reasons.length)
    const urgency = c.riskLevel === 'high' ? 100 : c.riskLevel === 'medium' ? 60 : 20
    const recency = urgencyScore(daysOld)
    const score = prioritize(confidence, es, Math.max(urgency, recency))
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
    const daysSince = Math.floor((Date.now() - new Date(rv.lastContactDate).getTime()) / 86400000)
    const daysOld = Math.floor((Date.now() - new Date(rv.lastContactDate).getTime()) / 86400000)
    const confidence = reactivationWindow(daysSince)
    const es = rv.whyContact ? 80 : 30
    const urgency = urgencyScore(daysOld)
    const score = prioritize(confidence, es, urgency)
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
