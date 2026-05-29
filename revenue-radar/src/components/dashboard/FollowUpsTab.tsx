'use client'

import { useState } from 'react'
import { Clock, Mail, AlertCircle } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { EmailDraftModal } from '@/components/email/EmailDraftModal'
import { MOCK_FOLLOWUPS } from '@/lib/mock-data'
import type { EmailDraftRequest } from '@/types'

interface FollowUp {
  id: string
  contactName: string
  company: string
  lastActivity: string
  daysInactive: number
  estimatedValue: string
  threadSubject: string
  urgency: 'high' | 'medium' | 'low'
}

interface Props {
  followUps?: FollowUp[]
  isDemo?: boolean
}

export function FollowUpsTab({ followUps, isDemo = false }: Props) {
  const data = isDemo ? MOCK_FOLLOWUPS : (followUps ?? [])
  const [draftRequest, setDraftRequest] = useState<EmailDraftRequest | null>(null)
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())

  const active = data.filter(f => !dismissed.has(f.id))

  const urgencyVariant = (u: string): 'danger' | 'warning' | 'secondary' => {
    if (u === 'high') return 'danger'
    if (u === 'medium') return 'warning'
    return 'secondary'
  }

  if (active.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <Clock className="w-12 h-12 mx-auto mb-3 opacity-40" />
        <p className="font-medium">No follow-ups needed</p>
        <p className="text-sm mt-1">All your conversations are up to date</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {isDemo && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-700">
          Demo data — connect Gmail to see your real stalled conversations
        </div>
      )}

      {active.map(fu => (
        <Card key={fu.id} className="hover:shadow-md transition-shadow">
          <CardContent className="p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className="font-semibold text-gray-900">{fu.contactName}</span>
                  <span className="text-gray-500 text-sm">· {fu.company}</span>
                  <Badge variant={urgencyVariant(fu.urgency)}>
                    {fu.urgency === 'high' ? '🔴' : '🟡'} {fu.urgency} urgency
                  </Badge>
                </div>

                <p className="text-sm text-gray-500 mb-2 truncate">{fu.threadSubject}</p>

                <div className="flex items-center gap-1 text-amber-600">
                  <AlertCircle className="w-3.5 h-3.5" />
                  <span className="text-sm font-medium">{fu.daysInactive} days without response</span>
                </div>
              </div>

              <div className="flex flex-col items-end gap-2 shrink-0">
                <span className="text-lg font-bold text-green-700">{fu.estimatedValue}</span>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setDismissed(prev => new Set(Array.from(prev).concat(fu.id)))}
                  >
                    Dismiss
                  </Button>
                  <Button
                    size="sm"
                    onClick={() =>
                      setDraftRequest({
                        to: `${fu.contactName} <${fu.contactName.toLowerCase().replace(' ', '.')}@${fu.company.toLowerCase().replace(/\s+/g, '')}.com>`,
                        context: `Following up on: "${fu.threadSubject}". This conversation has been inactive for ${fu.daysInactive} days. The estimated deal value is ${fu.estimatedValue}.`,
                        tone: 'professional',
                        signalType: 'followup',
                      })
                    }
                    className="bg-amber-500 hover:bg-amber-600 text-white"
                  >
                    <Mail className="w-3.5 h-3.5 mr-1" />
                    Follow Up
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
