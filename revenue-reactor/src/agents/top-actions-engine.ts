import type { BoardOpportunity, BoardChurnSignal, BoardReactivationTarget, TopAction } from '@/types'

function urgencyBonus(createdAtOrDate: string): number {
  const days = Math.floor((Date.now() - new Date(createdAtOrDate).getTime()) / 86400000)
  if (days <= 1) return 25
  if (days <= 3) return 15
  if (days <= 7) return 8
  return 0
}

function reactivationFreshnessBonus(lastContactDate: string): number {
  const days = Math.floor((Date.now() - new Date(lastContactDate).getTime()) / 86400000)
  // Fresher contacts rank higher (still recent enough to remember you)
  if (days < 60) return 20
  if (days < 120) return 14
  if (days < 180) return 8
  return 4
}

export function buildTopActions(
  opportunities: BoardOpportunity[],
  churnSignals: BoardChurnSignal[],
  reactivationTargets: BoardReactivationTarget[],
  limit = 10
): TopAction[] {
  const actions: TopAction[] = []

  for (const op of opportunities) {
    const confidence = op.revenueConfidence ?? op.opportunityScore
    const urgency = urgencyBonus(op.createdAt)
    const noisePenalty = op.opportunityScore < 50 ? 15 : 0
    // Formula: confidence * 0.45 + score * 0.35 + urgency - noise
    const priority = confidence * 0.45 + op.opportunityScore * 0.35 + urgency - noisePenalty
    actions.push({
      id: op.id,
      type: 'opportunity',
      name: op.contactName,
      company: op.company,
      priorityScore: Math.round(priority),
      revenueConfidence: op.revenueConfidence,
      estimatedValue: op.estimatedValue,
      reason: op.reason,
      action: op.suggestedAction,
    })
  }

  for (const c of churnSignals) {
    const urgency = urgencyBonus(c.createdAt)
    const riskBonus = c.riskLevel === 'high' ? 25 : c.riskLevel === 'medium' ? 12 : 0
    // Churn weighted heavily on score and risk level
    const priority = c.churnScore * 0.65 + urgency + riskBonus
    actions.push({
      id: c.id,
      type: 'churn',
      name: c.clientName,
      company: null,
      priorityScore: Math.round(priority),
      revenueConfidence: null,
      estimatedValue: null,
      reason: c.reasons[0] ?? c.whatHappened ?? '',
      action: c.recommendedAction,
      riskLevel: c.riskLevel,
    })
  }

  for (const rv of reactivationTargets) {
    const freshness = reactivationFreshnessBonus(rv.lastContactDate)
    // Base reactivation score — always worth doing, prioritize fresher contacts
    const priority = 45 + freshness
    actions.push({
      id: rv.id,
      type: 'reactivation',
      name: rv.contactName,
      company: rv.company,
      priorityScore: Math.round(priority),
      revenueConfidence: null,
      estimatedValue: null,
      reason: rv.whyContact ?? rv.history,
      action: rv.suggestedOffer,
    })
  }

  return actions.sort((a, b) => b.priorityScore - a.priorityScore).slice(0, limit)
}
