export interface OpportunitySignal {
  contactName: string
  company: string
  opportunityScore: number
  revenueConfidence: number
  estimatedValue: string
  reason: string
  evidence: string[]
  suggestedAction: string
}

export interface ChurnSignalResult {
  clientName: string
  churnScore: number
  riskLevel: 'low' | 'medium' | 'high'
  reasons: string[]
  whatHappened: string
  whyItMatters: string
  recommendedAction: string
}

export interface RetentionInsightResult {
  clientName: string
  insight: string
  suggestedMessage: string
  timing: string
}

export interface ReactivationResult {
  contactName: string
  email: string
  company: string
  lastContactDate: string
  history: string
  whyContact: string
  suggestedOffer: string
  suggestedMessage: string
}

export interface OutreachContact {
  name: string
  email: string
  company: string
  reason: string
  suggestedMessage: string
  priority: number
}

export interface TopAction {
  id: string
  type: 'opportunity' | 'churn' | 'reactivation'
  name: string
  company: string | null
  priorityScore: number
  revenueConfidence: number | null
  estimatedValue: string | null
  reason: string
  action: string
  riskLevel?: string
}

export interface RevenuePlanSection {
  items: { name: string; company: string | null; detail: string; value: string | null }[]
  estimatedTotal: string
}

export interface RevenuePlan {
  month: string
  generatedAt: string
  newRevenue: RevenuePlanSection
  saveRevenue: RevenuePlanSection
  reactivateRevenue: RevenuePlanSection
  totalPotential: string
}

export interface BoardData {
  isGmailConnected: boolean
  lastSyncAt: string | null
  topActions: TopAction[]
  opportunities: BoardOpportunity[]
  churnSignals: BoardChurnSignal[]
  retentionInsights: BoardRetentionInsight[]
  reactivationTargets: BoardReactivationTarget[]
  summary: BoardSummary
}

export interface BoardSummary {
  estimatedRevenue: string
  opportunityCount: number
  churnCount: number
  retentionCount: number
  reactivationCount: number
}

export interface BoardOpportunity {
  id: string
  contactName: string
  company: string | null
  opportunityScore: number
  revenueConfidence: number | null
  estimatedValue: string | null
  reason: string
  evidence: string[]
  suggestedAction: string
  status: string
  createdAt: string
}

export interface BoardChurnSignal {
  id: string
  clientName: string
  churnScore: number
  riskLevel: string
  reasons: string[]
  whatHappened: string | null
  whyItMatters: string | null
  recommendedAction: string
  status: string
  createdAt: string
}

export interface BoardRetentionInsight {
  id: string
  clientName: string
  insight: string
  suggestedMessage: string
  timing: string
  status: string
  createdAt: string
}

export interface BoardReactivationTarget {
  id: string
  contactName: string
  email: string
  company: string | null
  lastContactDate: string
  history: string
  whyContact: string | null
  suggestedOffer: string
  suggestedMessage: string
  status: string
}

export interface EmailThread {
  gmailThreadId: string
  subject: string
  snippet: string
  participants: string[]
  lastMessageAt: Date
  messages: EmailMessage[]
}

export interface EmailMessage {
  gmailMessageId: string
  from: string
  to: string[]
  subject: string
  bodyText: string
  sentAt: Date
}
