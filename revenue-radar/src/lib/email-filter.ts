import type { EmailThread } from '@/types'

const NEWSLETTER_PATTERNS = [
  /unsubscribe/i,
  /newsletter/i,
  /no.?reply@/i,
  /noreply@/i,
  /do.not.reply/i,
  /marketing@/i,
  /notifications@/i,
  /updates@/i,
  /news@/i,
  /info@/i,
  /hello@/i,
  /support@/i,
  /list-unsubscribe/i,
  /list-id:/i,
]

const AUTOMATED_SUBJECT_PATTERNS = [
  /order (confirmed|shipped|delivered)/i,
  /your (receipt|invoice|statement)/i,
  /payment (received|confirmation|failed)/i,
  /account (statement|summary)/i,
  /tracking number/i,
  /shipment/i,
  /automated (message|notification|email)/i,
  /do not reply/i,
  /\[automated\]/i,
  /digest$/i,
  /weekly (digest|summary|newsletter)/i,
  /monthly (report|newsletter|digest)/i,
]

const MARKETING_SUBJECT_PATTERNS = [
  /% off/i,
  /sale ends/i,
  /limited time/i,
  /exclusive offer/i,
  /free trial/i,
  /discount/i,
  /promo/i,
  /flash sale/i,
  /deal of the/i,
  /check out our/i,
]

const AUTOMATED_SENDER_DOMAINS = [
  'mailchimp.com',
  'constantcontact.com',
  'sendgrid.net',
  'mailgun.org',
  'amazonses.com',
  'bounce.',
  'mailer.',
  'em.salesforce.com',
  'hubspot.com',
  'marketo.com',
  'pardot.com',
  'klaviyo.com',
]

function extractEmail(address: string): string {
  const match = address.match(/<([^>]+)>/)
  return match ? match[1].toLowerCase() : address.toLowerCase()
}

function isAutomatedSender(from: string): boolean {
  const email = extractEmail(from)
  for (const domain of AUTOMATED_SENDER_DOMAINS) {
    if (email.includes(domain)) return true
  }
  for (const pattern of NEWSLETTER_PATTERNS) {
    if (pattern.test(email)) return true
  }
  return false
}

function hasPersonalName(from: string): boolean {
  const nameMatch = from.match(/^([^<@]+)\s*</)
  if (!nameMatch) return false
  const name = nameMatch[1].trim()
  return name.length > 2 && name.split(' ').length >= 1 && !/^(team|support|no.?reply|info|hello|news)/i.test(name)
}

export interface ClassificationResult {
  isHuman: boolean
  confidence: number
  reasons: string[]
}

export function classifyEmail(thread: EmailThread): ClassificationResult {
  const reasons: string[] = []
  let score = 0.5

  const firstMessage = thread.messages[0]
  if (!firstMessage) return { isHuman: false, confidence: 0.9, reasons: ['No messages'] }

  const from = firstMessage.from
  const subject = thread.subject
  const bodyText = firstMessage.bodyText

  // Hard disqualifiers
  if (isAutomatedSender(from)) {
    return { isHuman: false, confidence: 0.95, reasons: ['Automated sender detected'] }
  }

  for (const pattern of AUTOMATED_SUBJECT_PATTERNS) {
    if (pattern.test(subject)) {
      return { isHuman: false, confidence: 0.9, reasons: [`Automated subject: ${subject}`] }
    }
  }

  for (const pattern of MARKETING_SUBJECT_PATTERNS) {
    if (pattern.test(subject)) {
      return { isHuman: false, confidence: 0.85, reasons: [`Marketing subject: ${subject}`] }
    }
  }

  if (bodyText.includes('unsubscribe') && bodyText.includes('privacy policy')) {
    return { isHuman: false, confidence: 0.9, reasons: ['Newsletter footer detected'] }
  }

  // Positive signals
  if (hasPersonalName(from)) {
    score += 0.2
    reasons.push('Sender has personal name')
  }

  if (thread.participants.length >= 2 && thread.participants.length <= 10) {
    score += 0.15
    reasons.push('Normal conversation participant count')
  }

  if (thread.messages.length >= 2) {
    score += 0.1
    reasons.push('Multi-message thread (conversation)')
  }

  const bodyLower = bodyText.toLowerCase()
  const conversationalWords = ['thanks', 'hi ', 'hello', 'dear ', 'regards', 'best,', 'cheers', 'let me know', 'please', 'would you', 'can you', 'i wanted']
  const matchCount = conversationalWords.filter(w => bodyLower.includes(w)).length
  if (matchCount >= 2) {
    score += 0.1
    reasons.push('Conversational language detected')
  }

  const businessWords = ['project', 'proposal', 'meeting', 'call', 'quote', 'contract', 'invoice', 'budget', 'deadline', 'client', 'team', 'schedule']
  const bizMatchCount = businessWords.filter(w => bodyLower.includes(w)).length
  if (bizMatchCount >= 2) {
    score += 0.05
    reasons.push('Business context detected')
  }

  score = Math.min(0.99, Math.max(0.01, score))
  const threshold = 0.65

  return {
    isHuman: score >= threshold,
    confidence: score,
    reasons,
  }
}

export function filterHumanConversations(threads: EmailThread[]): EmailThread[] {
  return threads.filter(thread => {
    const result = classifyEmail(thread)
    return result.isHuman && result.confidence >= 0.65
  })
}
