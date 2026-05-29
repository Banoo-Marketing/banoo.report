export interface OpportunityResult {
  contact_name: string
  company: string
  opportunity_score: number
  estimated_value: string
  reason: string
  evidence: string[]
  recommended_action: string
}

export interface MissedFollowupResult {
  thread_id: string
  contact_name: string
  last_activity: string
  days_inactive: number
  estimated_value: string
  follow_up_needed: boolean
  recommended_email_draft: string
}

export interface ChurnResult {
  client: string
  churn_score: number
  risk_level: 'low' | 'medium' | 'high'
  reasons: string[]
  recommended_action: string
}

export interface ReactivationResult {
  contact: string
  email: string
  company: string
  last_contact_date: string
  reactivation_reason: string
  recommended_offer: string
  email_draft: string
}

export interface DailyReportResult {
  date: string
  new_opportunities: number
  follow_ups_needed: number
  churn_risks: number
  reactivation_targets: number
  estimated_revenue_at_risk: string
  top_actions: string[]
  summary: string
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

export interface EmailDraftRequest {
  to: string
  context: string
  tone?: 'professional' | 'friendly' | 'urgent'
  threadId?: string
  signalType: 'opportunity' | 'followup' | 'churn' | 'reactivation'
}

export interface GeneratedEmailDraft {
  subject: string
  body: string
  tone: string
}

export interface DashboardMetrics {
  totalOpportunities: number
  estimatedRevenue: string
  followUpsNeeded: number
  churnRisks: number
  reactivationTargets: number
  lastSyncAt: Date | null
  isGmailConnected: boolean
}

export interface ApiResponse<T> {
  data?: T
  error?: string
  message?: string
}
