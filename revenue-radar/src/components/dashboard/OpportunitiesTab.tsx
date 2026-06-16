'use client'

import { useState } from 'react'
import { TrendingUp, Mail, CheckCircle } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { EmailDraftModal } from '@/components/email/EmailDraftModal'
import { timeAgo, cn } from '@/lib/utils'
import { MOCK_OPPORTUNITIES } from '@/lib/mock-data'
import type { EmailDraftRequest } from '@/types'

interface Opportunity {
  id: string
  contactName: string
  company: string | null
  opportunityScore: number
  estimatedValue: string | null
  reason: string
  evidence: string[]
  recommendedAction: string
  status: string
  createdAt: string | Date
  thread?: { gmailThreadId: string; subject: string } | null
}

interface Props {
  opportunities?: Opportunity[]
  isDemo?: boolean
}

export function OpportunitiesTab({ opportunities, isDemo = false }: Props) {
  const data = isDemo ? MOCK_OPPORTUNITIES : (opportunities ?? [])
  const [draftRequest, setDraftRequest] = useState<EmailDraftRequest | null>(null)
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())

  const active = data.filter(o => !dismissed.has(o.id))

  const handleGenerateEmail = (op: (typeof data)[0]) => {
    setDraftRequest({
      to: op.contactName,
      context: `Contact: ${op.contactName} from ${op.company}. Opportunity: ${op.reason}. Recommended action: ${op.recommendedAction}`,
      tone: 'professional',
      threadId: op.thread?.gmailThreadId,
      signalType: 'opportunity',
    })
  }

  if (active.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <TrendingUp className="w-12 h-12 mx-auto mb-3 opacity-40" />
        <p className="font-medium">No opportunities detected yet</p>
        <p className="text-sm mt-1">Connect Gmail and sync to find revenue opportunities</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {isDemo && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-700">
          Demo data — connect Gmail to see your real opportunities
        </div>
      )}

      {active.map(op => (
        <Card key={op.id} className="hover:shadow-md transition-shadow">
          <CardContent className="p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-2">
                  <span className="font-semibold text-gray-900">{op.contactName}</span>
                  {op.company && <span className="text-gray-500 text-sm">· {op.company}</span>}
                  <Badge
                    variant={op.opportunityScore >= 75 ? 'success' : op.opportunityScore >= 50 ? 'warning' : 'outline'}
                    className="ml-auto"
                  >
                    Score: {op.opportunityScore}
                  </Badge>
                </div>

                <p className="text-sm text-gray-600 mb-2">{op.reason}</p>

                {op.evidence.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {op.evidence.slice(0, 3).map((e, i) => (
                      <span key={i} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                        {e}
                      </span>
                    ))}
                  </div>
                )}

                <p className="text-xs text-gray-500 italic">{op.recommendedAction}</p>
              </div>

              <div className="flex flex-col items-end gap-2 shrink-0">
                {op.estimatedValue && (
                  <span className="text-lg font-bold text-green-700">{op.estimatedValue}</span>
                )}
                <span className="text-xs text-gray-400">{timeAgo(op.createdAt)}</span>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setDismissed(prev => new Set(Array.from(prev).concat(op.id)))}
                    className="text-gray-500"
                  >
                    <CheckCircle className="w-3.5 h-3.5 mr-1" />
                    Done
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => handleGenerateEmail(op)}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    <Mail className="w-3.5 h-3.5 mr-1" />
                    Generate Email
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
