'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Brain, CheckCircle2, ClipboardList, ShieldCheck } from 'lucide-react'
import type { FactoryPlaybook, FactoryStatusResponse } from '@/lib/api'

interface PlaybookPanelProps {
  playbook: FactoryPlaybook | null
  factoryStatus: FactoryStatusResponse | null
  generating: boolean
  approving: boolean
  bridgeConnected: boolean
  onGenerate: () => Promise<void>
  onApprove: () => Promise<void>
}

export function PlaybookPanel({
  playbook,
  factoryStatus,
  generating,
  approving,
  bridgeConnected,
  onGenerate,
  onApprove,
}: PlaybookPanelProps) {
  const hasPlaybook = Boolean(playbook)

  return (
    <Card className="mt-4">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center">
          <Brain className="w-5 h-5 mr-2" />
          AI Factory Playbook
        </CardTitle>
        <CardDescription>
          {bridgeConnected ? 'Live factory/orchestrator state' : 'Bridge unavailable ,  showing no live playbook'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between gap-2">
          <Badge variant={hasPlaybook ? 'default' : 'secondary'}>
            {hasPlaybook ? 'Playbook Ready' : 'No Playbook Yet'}
          </Badge>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => void onGenerate()} disabled={generating}>
              <ClipboardList className="w-4 h-4 mr-2" />
              {generating ? 'Generating...' : 'Generate Demo'}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => void onApprove()}
              disabled={!hasPlaybook || approving}
            >
              <ShieldCheck className="w-4 h-4 mr-2" />
              {approving ? 'Approving...' : 'Approve'}
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="rounded border p-3">
            <div className="text-muted-foreground">Latest Title</div>
            <div className="font-medium">{factoryStatus?.latest_playbook_title ?? 'None'}</div>
          </div>
          <div className="rounded border p-3">
            <div className="text-muted-foreground">Action History</div>
            <div className="font-medium">{factoryStatus?.action_history_count ?? 0}</div>
          </div>
        </div>

        <div className="h-64 overflow-y-auto rounded border p-3">
          {hasPlaybook ? (
            <div className="space-y-3">
              <div>
                <div className="font-semibold">{playbook?.title}</div>
                <div className="text-sm text-muted-foreground">
                  Incident: {playbook?.incident_id} • Severity: {playbook?.severity ?? 'unknown'}
                </div>
              </div>

              <div>
                <div className="text-sm font-medium mb-1">Suggested actions</div>
                <ul className="space-y-1 text-sm">
                  {playbook?.suggested_actions.map((action) => (
                    <li key={action} className="flex gap-2">
                      <CheckCircle2 className="w-4 h-4 mt-0.5 text-green-600" />
                      <span>{action}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {!!playbook?.validation_checks?.length && (
                <div>
                  <div className="text-sm font-medium mb-1">Validation checks</div>
                  <ul className="list-disc pl-5 text-sm space-y-1">
                    {playbook.validation_checks.map((check) => (
                      <li key={check}>{check}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">
              Generate a demo playbook to surface the AI factory reasoning path here.
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
