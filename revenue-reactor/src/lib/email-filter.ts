import type { EmailThread } from '@/types'

const AUTO_SENDER = [/noreply@/i, /no-reply@/i, /notifications@/i, /updates@/i, /newsletter@/i, /marketing@/i, /mailchimp\.com/i, /sendgrid\.net/i, /hubspot\.com/i, /amazonses\.com/i]
const AUTO_SUBJECT = [/order (confirmed|shipped)/i, /your (receipt|invoice)/i, /payment (received|failed)/i, /tracking number/i, /automated/i, /do not reply/i, /\[digest\]/i, /weekly (digest|summary)/i]
const MARKETING_SUBJECT = [/% off/i, /limited time/i, /exclusive offer/i, /flash sale/i, /promo code/i]
const NEWSLETTER_BODY = ['unsubscribe', 'privacy policy', 'view in browser', 'email preferences']

function extractEmail(addr: string): string {
  return addr.match(/<([^>]+)>/)?.[1]?.toLowerCase() ?? addr.toLowerCase()
}

export function isHumanConversation(thread: EmailThread): boolean {
  const msg = thread.messages[0]
  if (!msg) return false
  const from = msg.from
  const email = extractEmail(from)
  const subject = thread.subject.toLowerCase()
  const body = msg.bodyText.toLowerCase()

  if (AUTO_SENDER.some(p => p.test(email))) return false
  if (AUTO_SUBJECT.some(p => p.test(subject))) return false
  if (MARKETING_SUBJECT.some(p => p.test(subject))) return false
  if (NEWSLETTER_BODY.filter(w => body.includes(w)).length >= 2) return false

  let score = 0
  if (/^[^<@]+\s+[^<@]+\s*</.test(from)) score += 2
  if (thread.messages.length >= 2 && thread.messages.length <= 15) score += 2
  if (thread.participants.length >= 2 && thread.participants.length <= 8) score += 1
  const conversational = ['hi ', 'hello', 'thanks', 'dear ', 'regards', 'let me know', 'please', 'would you']
  if (conversational.filter(w => body.includes(w)).length >= 2) score += 2
  const business = ['project', 'proposal', 'quote', 'meeting', 'budget', 'client', 'contract', 'invoice', 'timeline']
  if (business.filter(w => body.includes(w)).length >= 1) score += 1

  return score >= 3
}
