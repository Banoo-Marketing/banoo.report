export interface OpportunitySignal {
  contactName: string
  company: string
  opportunityScore: number
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

export interface BoardData {
  isGmailConnected: boolean
  lastSyncAt: string | null
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
