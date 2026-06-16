import { google } from 'googleapis'
import { decrypt } from './crypto'
import type { EmailThread, EmailMessage } from '@/types'

const SCOPES = [
  'https://www.googleapis.com/auth/gmail.readonly',
  'https://www.googleapis.com/auth/gmail.send',
]

export function createOAuthClient() {
  return new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    `${process.env.NEXTAUTH_URL}/api/auth/callback/google`
  )
}

export function getAuthClient(encryptedAccessToken: string, encryptedRefreshToken: string) {
  const auth = createOAuthClient()
  auth.setCredentials({
    access_token: decrypt(encryptedAccessToken),
    refresh_token: decrypt(encryptedRefreshToken),
  })
  return auth
}

function decodeBase64(data: string): string {
  return Buffer.from(data.replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf-8')
}

function extractBody(payload: { mimeType?: string | null; body?: { data?: string | null } | null; parts?: { mimeType?: string | null; body?: { data?: string | null } | null }[] | null }): string {
  if (payload.mimeType === 'text/plain' && payload.body?.data) {
    return decodeBase64(payload.body.data)
  }
  if (payload.parts) {
    for (const part of payload.parts) {
      if (part.mimeType === 'text/plain' && part.body?.data) {
        return decodeBase64(part.body.data)
      }
    }
    for (const part of payload.parts) {
      if (part.mimeType === 'multipart/alternative' || part.mimeType === 'multipart/mixed') {
        const nested = extractBody(part)
        if (nested) return nested
      }
    }
  }
  return ''
}

function getHeader(headers: { name?: string | null; value?: string | null }[], name: string): string {
  return headers.find(h => h.name?.toLowerCase() === name.toLowerCase())?.value ?? ''
}

export async function fetchThreads(
  auth: ReturnType<typeof getAuthClient>,
  options: { maxResults?: number; historyId?: string; pageToken?: string } = {}
): Promise<{ threads: { id: string; historyId: string }[]; nextPageToken?: string; historyId: string }> {
  const gmail = google.gmail({ version: 'v1', auth })

  const listRes = await gmail.users.threads.list({
    userId: 'me',
    maxResults: options.maxResults ?? 50,
    pageToken: options.pageToken,
    q: '-category:promotions -category:updates -category:social -category:forums',
  })

  const threads = (listRes.data.threads ?? []).map(t => ({
    id: t.id ?? '',
    historyId: '',
  }))

  return {
    threads,
    nextPageToken: listRes.data.nextPageToken ?? undefined,
    historyId: '',
  }
}

export async function fetchThreadDetails(
  auth: ReturnType<typeof getAuthClient>,
  threadId: string
): Promise<EmailThread | null> {
  const gmail = google.gmail({ version: 'v1', auth })

  try {
    const threadRes = await gmail.users.threads.get({
      userId: 'me',
      id: threadId,
      format: 'full',
    })

    const thread = threadRes.data
    if (!thread.messages || thread.messages.length === 0) return null

    const participants = new Set<string>()
    const messages: EmailMessage[] = []

    for (const msg of thread.messages) {
      const headers = msg.payload?.headers ?? []
      const from = getHeader(headers, 'from')
      const toRaw = getHeader(headers, 'to')
      const subject = getHeader(headers, 'subject')
      const date = getHeader(headers, 'date')
      const bodyText = msg.payload ? extractBody(msg.payload) : ''

      if (from) participants.add(from)
      const toList = toRaw.split(',').map(e => e.trim()).filter(Boolean)
      toList.forEach(e => participants.add(e))

      messages.push({
        gmailMessageId: msg.id ?? '',
        from,
        to: toList,
        subject,
        bodyText: bodyText.slice(0, 5000),
        sentAt: date ? new Date(date) : new Date(),
      })
    }

    const lastMsg = thread.messages[thread.messages.length - 1]
    const lastHeaders = lastMsg.payload?.headers ?? []
    const lastDate = getHeader(lastHeaders, 'date')
    const subject = getHeader(thread.messages[0].payload?.headers ?? [], 'subject')
    const snippet = thread.snippet ?? ''

    return {
      gmailThreadId: thread.id ?? '',
      subject,
      snippet,
      participants: Array.from(participants),
      lastMessageAt: lastDate ? new Date(lastDate) : new Date(),
      messages,
    }
  } catch {
    return null
  }
}

export async function fetchIncrementalChanges(
  auth: ReturnType<typeof getAuthClient>,
  startHistoryId: string
): Promise<{ threadIds: string[]; newHistoryId: string }> {
  const gmail = google.gmail({ version: 'v1', auth })

  try {
    const historyRes = await gmail.users.history.list({
      userId: 'me',
      startHistoryId,
      historyTypes: ['messageAdded'],
    })

    const threadIds = new Set<string>()
    for (const record of historyRes.data.history ?? []) {
      for (const msg of record.messagesAdded ?? []) {
        if (msg.message?.threadId) threadIds.add(msg.message.threadId)
      }
    }

    return {
      threadIds: Array.from(threadIds),
      newHistoryId: historyRes.data.historyId ?? startHistoryId,
    }
  } catch {
    return { threadIds: [], newHistoryId: startHistoryId }
  }
}

export async function sendEmail(
  auth: ReturnType<typeof getAuthClient>,
  params: { to: string; subject: string; body: string; threadId?: string }
): Promise<{ messageId: string; threadId: string }> {
  const gmail = google.gmail({ version: 'v1', auth })

  const messageParts = [
    `To: ${params.to}`,
    'Content-Type: text/plain; charset=utf-8',
    'MIME-Version: 1.0',
    `Subject: ${params.subject}`,
    '',
    params.body,
  ]

  const message = messageParts.join('\n')
  const encodedMessage = Buffer.from(message).toString('base64url')

  const res = await gmail.users.messages.send({
    userId: 'me',
    requestBody: {
      raw: encodedMessage,
      threadId: params.threadId,
    },
  })

  return {
    messageId: res.data.id ?? '',
    threadId: res.data.threadId ?? '',
  }
}

export async function getGmailProfile(auth: ReturnType<typeof getAuthClient>): Promise<{ email: string; historyId: string }> {
  const gmail = google.gmail({ version: 'v1', auth })
  const profile = await gmail.users.getProfile({ userId: 'me' })
  return {
    email: profile.data.emailAddress ?? '',
    historyId: profile.data.historyId ?? '',
  }
}
