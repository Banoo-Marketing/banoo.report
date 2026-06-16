import { NextResponse } from 'next/server'
import { requireSession } from '@/lib/session'
import { prisma } from '@/lib/db'
import { getAuthClient, sendEmail } from '@/lib/gmail'

export async function POST(req: Request) {
  const { session, error } = await requireSession()
  if (error) return error

  const userId = session!.user!.id!
  const { draftId } = await req.json() as { draftId: string }

  const draft = await prisma.emailDraft.findFirst({ where: { id: draftId, userId } })
  if (!draft) {
    return NextResponse.json({ error: 'Draft not found' }, { status: 404 })
  }

  if (draft.status === 'SENT') {
    return NextResponse.json({ error: 'Email already sent' }, { status: 400 })
  }

  const gmailToken = await prisma.gmailToken.findUnique({ where: { userId } })
  if (!gmailToken) {
    return NextResponse.json({ error: 'Gmail not connected' }, { status: 400 })
  }

  const auth = getAuthClient(gmailToken.accessToken, gmailToken.refreshToken)

  try {
    const result = await sendEmail(auth, {
      to: draft.to,
      subject: draft.subject,
      body: draft.body,
      threadId: draft.threadId ?? undefined,
    })

    await prisma.emailDraft.update({
      where: { id: draftId },
      data: { status: 'SENT', sentAt: new Date() },
    })

    return NextResponse.json({ success: true, messageId: result.messageId })
  } catch (err) {
    console.error('Send email error:', err)
    return NextResponse.json({ error: 'Failed to send email' }, { status: 500 })
  }
}
