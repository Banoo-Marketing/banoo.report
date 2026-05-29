import { google } from 'googleapis'
import { decrypt } from './crypto'
import type { EmailThread, EmailMessage } from '@/types'

export function getAuthClient(encryptedAccess: string, encryptedRefresh: string) {
  const auth = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    `${process.env.NEXTAUTH_URL}/api/auth/callback/google`
  )
  auth.setCredentials({ access_token: decrypt(encryptedAccess), refresh_token: decrypt(encryptedRefresh) })
  return auth
}

type GmailAuth = ReturnType<typeof getAuthClient>

function decodeBase64(data: string): string {
  return Buffer.from(data.replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf-8')
}

type MsgPart = {
  mimeType?: string | null
  body?: { data?: string | null } | null
  parts?: MsgPart[] | null
}

function extractBody(payload: MsgPart): string {
  if (payload.mimeType === 'text/plain' && payload.body?.data) return decodeBase64(payload.body.data)
  for (const part of payload.parts ?? []) {
    if (part.mimeType === 'text/plain' && part.body?.data) return decodeBase64(part.body.data)
  }
  for (const part of payload.parts ?? []) {
    if (part.mimeType?.startsWith('multipart/')) {
      const nested = extractBody(part)
      if (nested) return nested
    }
  }
  return ''
}

function header(headers: { name?: string | null; value?: string | null }[], name: string): string {
  return headers.find(h => h.name?.toLowerCase() === name.toLowerCase())?.value ?? ''
}

export async function listThreadIds(auth: GmailAuth, maxResults = 50): Promise<{ ids: string[]; historyId: string }> {
  const gmail = google.gmail({ version: 'v1', auth })
  const res = await gmail.users.threads.list({
    userId: 'me',
    maxResults,
    q: '-category:promotions -category:updates -category:social -category:forums',
  })
  const profile = await gmail.users.getProfile({ userId: 'me' })
  return {
    ids: (res.data.threads ?? []).map(t => t.id ?? '').filter(Boolean),
    historyId: profile.data.historyId ?? '',
  }
}

export async function getIncrementalThreadIds(auth: GmailAuth, startHistoryId: string): Promise<{ ids: string[]; historyId: string }> {
  const gmail = google.gmail({ version: 'v1', auth })
  try {
    const res = await gmail.users.history.list({ userId: 'me', startHistoryId, historyTypes: ['messageAdded'] })
    const ids = new Set<string>()
    for (const r of res.data.history ?? []) {
      for (const m of r.messagesAdded ?? []) {
        if (m.message?.threadId) ids.add(m.message.threadId)
      }
    }
    return { ids: Array.from(ids), historyId: res.data.historyId ?? startHistoryId }
  } catch {
    return { ids: [], historyId: startHistoryId }
  }
}

export async function getThread(auth: GmailAuth, threadId: string): Promise<EmailThread | null> {
  const gmail = google.gmail({ version: 'v1', auth })
  try {
    const res = await gmail.users.threads.get({ userId: 'me', id: threadId, format: 'full' })
    const thread = res.data
    if (!thread.messages?.length) return null

    const participants = new Set<string>()
    const messages: EmailMessage[] = []

    for (const msg of thread.messages) {
      const hdrs = msg.payload?.headers ?? []
      const from = header(hdrs, 'from')
      const toRaw = header(hdrs, 'to')
      const subject = header(hdrs, 'subject')
      const date = header(hdrs, 'date')
      const bodyText = msg.payload ? extractBody(msg.payload as MsgPart) : ''
      if (from) participants.add(from)
      const toList = toRaw.split(',').map(e => e.trim()).filter(Boolean)
      toList.forEach(e => participants.add(e))
      messages.push({
        gmailMessageId: msg.id ?? '',
        from,
        to: toList,
        subject,
        bodyText: bodyText.slice(0, 4000),
        sentAt: date ? new Date(date) : new Date(),
      })
    }

    const firstHdrs = thread.messages[0].payload?.headers ?? []
    const lastHdrs = thread.messages[thread.messages.length - 1].payload?.headers ?? []
    const lastDate = header(lastHdrs, 'date')

    return {
      gmailThreadId: thread.id ?? '',
      subject: header(firstHdrs, 'subject'),
      snippet: thread.snippet ?? '',
      participants: Array.from(participants),
      lastMessageAt: lastDate ? new Date(lastDate) : new Date(),
      messages,
    }
  } catch {
    return null
  }
}
