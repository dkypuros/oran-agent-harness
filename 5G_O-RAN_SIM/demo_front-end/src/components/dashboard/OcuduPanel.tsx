'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Layers3 } from 'lucide-react'
import type {
  OcuduActionRecord,
  OcuduAppsResponse,
  OcuduConfigsResponse,
  OcuduContextResponse,
  OcuduEvidenceRecord,
  OcuduSupportedActionsResponse,
  OcuduStatusResponse,
} from '@/lib/api'
import { useEffect, useMemo, useState } from 'react'

interface OcuduPanelProps {
  status: OcuduStatusResponse | null
  apps: OcuduAppsResponse | null
  configs: OcuduConfigsResponse | null
  context: OcuduContextResponse | null
  supportedActions: OcuduSupportedActionsResponse | null
  latestAction: OcuduActionRecord | null
  latestEvidence: OcuduEvidenceRecord | null
  submitting: boolean
  onSubmit: (actionType: string, parameters?: Record<string, unknown>) => Promise<void>
  bridgeConnected: boolean
}

export function OcuduPanel({
  status,
  apps,
  configs,
  context,
  supportedActions,
  latestAction,
  latestEvidence,
  submitting,
  onSubmit,
  bridgeConnected,
}: OcuduPanelProps) {
  const effectiveStatus = context?.status ?? status
  const effectiveApps = context?.apps ?? apps
  const effectiveConfigs = context?.configs ?? configs
  const actions = useMemo(() => supportedActions?.actions ?? [], [supportedActions])
  const [selectedActionType, setSelectedActionType] = useState('')
  const [inventoryLimit, setInventoryLimit] = useState('10')

  useEffect(() => {
    if (!selectedActionType && actions[0]?.action_type) {
      setSelectedActionType(actions[0].action_type)
    }
  }, [actions, selectedActionType])

  const selectedAction = useMemo(
    () => actions.find((action) => action.action_type === selectedActionType) ?? null,
    [actions, selectedActionType]
  )

  const selectedParameters =
    selectedActionType === 'collect_app_inventory' || selectedActionType === 'collect_config_inventory'
      ? { limit: Number.parseInt(inventoryLimit || '10', 10) || 10 }
      : undefined

  return (
    <Card className="mt-4">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center">
          <Layers3 className="w-5 h-5 mr-2" />
          OCUDU Integration
        </CardTitle>
        <CardDescription>
          {bridgeConnected
            ? 'Safe reference lane surfaced through the prototype bridge'
            : 'Bridge unavailable ,  OCUDU status unavailable'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded border p-3 text-sm">
          <div className="font-medium">Lane role</div>
          <div className="text-muted-foreground">
            OCUDU is the safe evidence-bearing reference lane, not the primary live execution path.
          </div>
        </div>
        <div className="flex items-center justify-between">
          <Badge variant={effectiveStatus?.present ? 'default' : 'secondary'}>
            {effectiveStatus?.present ? 'Checkout Present' : 'Not Present'}
          </Badge>
          <span className="text-sm text-muted-foreground">
            {effectiveStatus?.branch ?? 'unknown'} {effectiveStatus?.head_short ? `(${effectiveStatus.head_short})` : ''}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="rounded border p-3">
            <div className="text-muted-foreground">Apps</div>
            <div className="font-medium">{effectiveStatus?.app_count ?? effectiveApps?.count ?? 0}</div>
          </div>
          <div className="rounded border p-3">
            <div className="text-muted-foreground">Configs</div>
            <div className="font-medium">{effectiveStatus?.config_count ?? effectiveConfigs?.count ?? 0}</div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="rounded border p-3">
            <div className="text-muted-foreground">Integration Role</div>
            <div className="font-medium">{context?.integration_role ?? 'unknown'}</div>
          </div>
          <div className="rounded border p-3">
            <div className="text-muted-foreground">Libraries</div>
            <div className="font-medium">{effectiveStatus?.lib_present ? 'present' : 'not present'}</div>
          </div>
        </div>

        <div className="rounded border p-3 text-sm">
          <div className="font-medium mb-2">Sample apps</div>
          <div className="text-muted-foreground">
            {effectiveApps?.apps?.slice(0, 5).join(', ') || 'none'}
          </div>
        </div>

        <div className="rounded border p-3 text-sm">
          <div className="font-medium mb-2">Sample configs</div>
          <div className="text-muted-foreground">
            {effectiveConfigs?.configs?.slice(0, 5).join(', ') || 'none'}
          </div>
        </div>

        <div className="rounded border p-3 text-sm">
          <div className="font-medium mb-2">Next step</div>
          <div className="text-muted-foreground">
            {context?.next_step ?? 'No OCUDU next-step guidance available'}
          </div>
        </div>

        <div className="rounded border p-3 text-sm space-y-3">
          <div className="font-medium">OCUDU actions</div>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded border p-3">
              <div className="text-muted-foreground">Supported Actions</div>
              <div className="font-medium">{supportedActions?.count ?? 0}</div>
            </div>
            <div className="rounded border p-3">
              <div className="text-muted-foreground">Latest Verification</div>
              <div className="font-medium">{latestEvidence?.verification_status ?? 'none yet'}</div>
            </div>
          </div>

          <Select value={selectedActionType} onValueChange={setSelectedActionType}>
            <SelectTrigger>
              <SelectValue placeholder="Select OCUDU action" />
            </SelectTrigger>
            <SelectContent>
              {actions.map((action) => (
                <SelectItem key={action.action_type} value={action.action_type}>
                  {action.action_type}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="rounded border p-3 text-sm">
            <div className="font-medium">{selectedAction?.summary ?? 'No OCUDU action selected'}</div>
            <div className="text-muted-foreground">
              Target: {selectedAction?.target_system ?? 'unknown'} • Approval required:{' '}
              {selectedAction?.approval_required ? 'yes' : 'no'}
            </div>
          </div>
          {(selectedActionType === 'collect_app_inventory' || selectedActionType === 'collect_config_inventory') && (
            <div className="rounded border p-3 text-sm space-y-2">
              <Label htmlFor="ocudu-inventory-limit">Inventory limit</Label>
              <Input
                id="ocudu-inventory-limit"
                type="number"
                min={1}
                max={20}
                value={inventoryLimit}
                onChange={(event) => setInventoryLimit(event.target.value)}
              />
              <div className="text-muted-foreground">Control how many OCUDU apps or configs are returned.</div>
            </div>
          )}

          <Button
            className="w-full"
            disabled={!selectedActionType || submitting || !bridgeConnected}
            onClick={() => void onSubmit(selectedActionType, selectedParameters)}
          >
            {submitting ? 'Submitting...' : 'Run OCUDU Action'}
          </Button>

          <div className="rounded border p-3 text-sm space-y-2">
            <div className="font-medium">Latest OCUDU action</div>
            {latestAction ? (
              <>
                <div>{latestAction.summary ?? latestAction.action_type}</div>
                <div className="text-muted-foreground break-all">
                  {latestAction.action_id} • {latestAction.status ?? 'unknown'}
                </div>
                <div>{latestAction.result_summary ?? latestEvidence?.result_summary ?? 'No result summary yet'}</div>
                {!!latestAction.error_message && (
                  <div className="rounded border border-red-200 bg-red-50 p-2 text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
                    {latestAction.error_message}
                  </div>
                )}
              </>
            ) : (
              <div className="text-muted-foreground">No OCUDU action has been submitted yet.</div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
