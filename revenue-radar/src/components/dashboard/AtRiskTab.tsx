'use client'

import { useState } from 'react'
import { AlertTriangle, Mail, Shield } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { EmailDraftModal } from '@/components/email/EmailDraftModal'
import { MOCK_CHURN } from '@/lib/mock-data'
import { riskLevelVariant, timeAgo } from '@/lib/utils'
import type { EmailDraftRequest } from '@/types'

interface ChurnSignal {
  id: string
  client: string
  churnScore: number
  riskLevel: string
  reasons: string[]
  recommendedAction: string
  status: string
  createdAt: string | Date
}

interface Props {
  signals?: ChurnSignal[]
  isDemo?: boolean
}

export function AtRiskTab({ signals, isDemo = false }: Props) {
  const data = isDemo ? MOCK_CHURN : (signals ?? [])
  const [draftRequest, setDraftRequest] = useState<EmailDraftRequest | null>(null)
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())

  const active = data.filter(s => !dismissed.has(s.id))

  if (active.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <Shield className="w-12 h-12 mx-auto mb-3 opacity-40" />
        <p className="font-medium">No clients at risk</p>
        <p className="text-sm mt-1">Your client relationships look healthy</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {isDemo && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-700">
          Demo data — connect Gmail to detect real churn risks
        </div>
      )}

      {active.map(signal => (
        <Card key={signal.id} className={`hover:shadow-md transition-shadow border-l-4 ${signal.riskLevel === 'high' ? 'border-l-red-500' : signal.riskLevel === 'medium' ? 'border-l-yellow-500' : 'border-l-green-500'}`}>
          <CardContent className="p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-2">
                  <span className="font-semibold text-gray-900">{signal.client}</span>
                  <Badge variant={riskLevelVariant(signal.riskLevel)}>
                    {signal.riskLevel.toUpperCase()} RISK
                  </Badge>
                  <span className="text-sm text-gray-500 ml-auto">Churn score: {signal.churnScore}/100</span>
                </div>

                <div className="mb-2">
                  {signal.reasons.map((reason, i) => (
                    <div key={i} className="flex items-center gap-1 text-sm text-gray-600 mb-0.5">
                      <AlertTriangle className="w-3 h-3 text-red-400 shrink-0" />
                      {reason}
                    </div>
                  ))}
                </div>

                <p className="text-xs text-gray-500 italic bg-gray-50 rounded p-2">{signal.recommendedAction}</p>
              </div>

              <div className="flex flex-col items-end gap-2 shrink-0">
                <span className="text-xs text-gray-400">{timeAgo(signal.createdAt)}</span>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setDismissed(prev => new Set(Array.from(prev).concat(signal.id)))}
                  >
                    Resolved
                  </Button>
                  <Button
                    size="sm"
                    onClick={() =>
                      setDraftRequest({
                        to: signal.client,
                        context: `Client ${signal.client} shows churn risk (score: ${signal.churnScore}/100). Reasons: ${signal.reasons.join(', ')}. Recommended action: ${signal.recommendedAction}`,
                        tone: 'professional',
                        signalType: 'churn',
                      })
                    }
                    className="bg-red-600 hover:bg-red-700 text-white"
                  >
                    <Mail className="w-3.5 h-3.5 mr-1" />
                    Reach Out
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
