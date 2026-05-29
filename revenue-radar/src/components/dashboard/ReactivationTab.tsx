'use client'

import { useState } from 'react'
import { Users, Mail, Clock } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { EmailDraftModal } from '@/components/email/EmailDraftModal'
import { MOCK_REACTIVATIONS } from '@/lib/mock-data'
import { formatDate } from '@/lib/utils'
import type { EmailDraftRequest } from '@/types'

interface ReactivationContact {
  id: string
  name: string
  email: string
  company: string | null
  lastContactDate: string | Date
  reactivationReason: string
  recommendedOffer: string
  emailDraft: string
  status: string
}

interface Props {
  contacts?: ReactivationContact[]
  isDemo?: boolean
}

export function ReactivationTab({ contacts, isDemo = false }: Props) {
  const data = isDemo ? MOCK_REACTIVATIONS : (contacts ?? [])
  const [draftRequest, setDraftRequest] = useState<EmailDraftRequest | null>(null)
  const [previewId, setPreviewId] = useState<string | null>(null)
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())

  const active = data.filter(c => !dismissed.has(c.id))

  const daysSince = (date: string | Date) => {
    return Math.floor((Date.now() - new Date(date).getTime()) / (1000 * 60 * 60 * 24))
  }

  if (active.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <Users className="w-12 h-12 mx-auto mb-3 opacity-40" />
        <p className="font-medium">No reactivation opportunities</p>
        <p className="text-sm mt-1">Past clients and cold leads will appear here</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {isDemo && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-700">
          Demo data — connect Gmail to find your real reactivation opportunities
        </div>
      )}

      {active.map(contact => (
        <Card key={contact.id} className="hover:shadow-md transition-shadow">
          <CardContent className="p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className="font-semibold text-gray-900">{contact.name}</span>
                  {contact.company && <span className="text-gray-500 text-sm">· {contact.company}</span>}
                  <Badge variant="secondary" className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {daysSince(contact.lastContactDate)}d inactive
                  </Badge>
                </div>

                <p className="text-xs text-gray-500 mb-1">{contact.email}</p>
                <p className="text-sm text-gray-600 mb-2">{contact.reactivationReason}</p>
                <p className="text-xs bg-purple-50 text-purple-700 rounded px-2 py-1 inline-block">
                  💡 {contact.recommendedOffer}
                </p>

                {previewId === contact.id && (
                  <div className="mt-3 bg-gray-50 rounded-md p-3 text-sm text-gray-700 whitespace-pre-wrap border">
                    {contact.emailDraft}
                  </div>
                )}
              </div>

              <div className="flex flex-col items-end gap-2 shrink-0">
                <span className="text-xs text-gray-400">
                  Last contact: {formatDate(contact.lastContactDate)}
                </span>
                <div className="flex gap-2 flex-wrap justify-end">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setPreviewId(previewId === contact.id ? null : contact.id)}
                  >
                    {previewId === contact.id ? 'Hide Draft' : 'Preview Draft'}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setDismissed(prev => new Set(Array.from(prev).concat(contact.id)))}
                  >
                    Skip
                  </Button>
                  <Button
                    size="sm"
                    onClick={() =>
                      setDraftRequest({
                        to: contact.email,
                        context: `Reactivating: ${contact.name} from ${contact.company}. Last contact: ${formatDate(contact.lastContactDate)}. Reason: ${contact.reactivationReason}. Offer: ${contact.recommendedOffer}`,
                        tone: 'friendly',
                        signalType: 'reactivation',
                      })
                    }
                    className="bg-purple-600 hover:bg-purple-700 text-white"
                  >
                    <Mail className="w-3.5 h-3.5 mr-1" />
                    Send Outreach
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}

      <EmailDraftModal
        open={!!draftRequest}
        onClose={() => setDraftRequest(null)}
        request={draftRequest}
      />
    </div>
  )
}
