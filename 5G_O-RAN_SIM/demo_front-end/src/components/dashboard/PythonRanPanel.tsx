'use client'

import { useEffect, useMemo, useState } from 'react'
import { Activity, CheckCircle2, Clock3, PlayCircle, ShieldCheck, XCircle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type {
  PythonRanActionRecord,
  PythonRanEvidenceRecord,
  PythonRanSupportedActionsResponse,
} from '@/lib/api'

interface PythonRanPanelProps {
  supportedActions: PythonRanSupportedActionsResponse | null
  latestAction: PythonRanActionRecord | null
  latestEvidence: PythonRanEvidenceRecord | null
  bridgeConnected: boolean
  submitting: boolean
  approving: boolean
  onSubmit: (actionType: string, parameters?: Record<string, unknown>) => Promise<void>
  onApprove: (actionId: string) => Promise<void>
}

export function PythonRanPanel({
  supportedActions,
  latestAction,
  latestEvidence,
  bridgeConnected,
  submitting,
  approving,
  onSubmit,
  onApprove,
}: PythonRanPanelProps) {
  const actions = useMemo(() => supportedActions?.actions ?? [], [supportedActions])
  const defaultActionType = useMemo(() => actions[0]?.action_type ?? '', [actions])
  const [selectedActionType, setSelectedActionType] = useState('')
  const [logLimit, setLogLimit] = useState('5')
  const [nasPdu, setNasPdu] = useState('registration-request')
  const [rrcContainer, setRrcContainer] = useState('rrc-setup-request')
  const [rrcTransactionId, setRrcTransactionId] = useState('1')
  const [gnbDuUeF1apId, setGnbDuUeF1apId] = useState('1')
  const [preambleIndex, setPreambleIndex] = useState('0')

  useEffect(() => {
    if (!selectedActionType && defaultActionType) {
      setSelectedActionType(defaultActionType)
    }
  }, [defaultActionType, selectedActionType])

  const selectedAction = useMemo(
    () => actions.find((action) => action.action_type === selectedActionType) ?? null,
    [actions, selectedActionType]
  )

  const latestStatusVariant =
    latestAction?.status === 'completed'
      ? 'default'
      : latestAction?.status === 'failed'
        ? 'destructive'
        : 'secondary'

  const latestVerificationVariant =
    latestEvidence?.verification_status === 'passed'
      ? 'default'
      : latestEvidence?.verification_status === 'failed'
        ? 'destructive'
        : 'secondary'

  const latestStatusIcon =
    latestAction?.status === 'completed' ? (
      <CheckCircle2 className="w-4 h-4 text-green-600" />
    ) : latestAction?.status === 'failed' ? (
      <XCircle className="w-4 h-4 text-red-600" />
    ) : (
      <Clock3 className="w-4 h-4 text-amber-600" />
    )

  const canApprove = Boolean(
    latestAction?.action_id && latestAction?.status === 'submitted' && latestAction?.approval_required
  )

  const selectedParameters = useMemo(() => {
    switch (selectedActionType) {
      case 'collect_logs':
        return { limit: Number.parseInt(logLimit || '5', 10) || 5 }
      case 'gnb_initial_ue_message':
        return { nas_pdu: nasPdu || 'registration-request' }
      case 'du_initial_ul_rrc_message':
        return { rrcContainer: rrcContainer || 'rrc-setup-request' }
      case 'cu_create_rrc_setup':
        return {
          rrcTransactionId: Number.parseInt(rrcTransactionId || '1', 10) || 1,
          gnbDuUeF1apId: Number.parseInt(gnbDuUeF1apId || '1', 10) || 1,
        }
      case 'du_process_prach':
        return { preamble_index: Number.parseInt(preambleIndex || '0', 10) || 0 }
      default:
        return undefined
    }
  }, [gnbDuUeF1apId, logLimit, nasPdu, preambleIndex, rrcContainer, rrcTransactionId, selectedActionType])

  return (
    <Card className="mt-4">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center">
          <Activity className="w-5 h-5 mr-2" />
          Python RAN Actions
        </CardTitle>
        <CardDescription>
          {bridgeConnected
            ? 'Primary live execution lane over the bridge'
            : 'Bridge unavailable ,  python RAN actions unavailable'}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded border p-3 text-sm">
          <div className="font-medium">Lane role</div>
          <div className="text-muted-foreground">
            Python RAN is the primary live execution lane for action, approval, and evidence flow.
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="rounded border p-3">
            <div className="text-muted-foreground">Supported Actions</div>
            <div className="font-medium">{supportedActions?.count ?? 0}</div>
          </div>
          <div className="rounded border p-3">
            <div className="text-muted-foreground">Latest Verification</div>
            <div className="font-medium">{latestEvidence?.verification_status ?? 'none yet'}</div>
          </div>
        </div>

        <div className="space-y-2">
          <div className="text-sm font-medium">Run python RAN action</div>
          <Select value={selectedActionType} onValueChange={setSelectedActionType}>
            <SelectTrigger>
              <SelectValue placeholder="Select python RAN action" />
            </SelectTrigger>
            <SelectContent>
              {actions.map((action) => (
                <SelectItem key={action.action_type} value={action.action_type}>
                  {action.action_type}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="rounded border p-3 text-sm space-y-1">
            <div className="font-medium">{selectedAction?.summary ?? 'No action selected'}</div>
            <div className="text-muted-foreground">
              Component: {selectedAction?.component ?? 'unknown'} • Approval required:{' '}
              {selectedAction?.approval_required ? 'yes' : 'no'}
            </div>
          </div>
          {selectedActionType === 'collect_logs' && (
            <div className="rounded border p-3 text-sm space-y-2">
              <Label htmlFor="python-ran-log-limit">Log limit</Label>
              <Input
                id="python-ran-log-limit"
                type="number"
                min={1}
                max={20}
                value={logLimit}
                onChange={(event) => setLogLimit(event.target.value)}
              />
              <div className="text-muted-foreground">Control how many log artifacts are requested from the bridge.</div>
            </div>
          )}
          {selectedActionType === 'gnb_initial_ue_message' && (
            <div className="rounded border p-3 text-sm space-y-2">
              <Label htmlFor="python-ran-nas-pdu">NAS PDU</Label>
              <Input
                id="python-ran-nas-pdu"
                value={nasPdu}
                onChange={(event) => setNasPdu(event.target.value)}
              />
              <div className="text-muted-foreground">Provide the NAS payload used for the gNB initial UE message flow.</div>
            </div>
          )}
          {selectedActionType === 'du_initial_ul_rrc_message' && (
            <div className="rounded border p-3 text-sm space-y-2">
              <Label htmlFor="python-ran-rrc-container">RRC container</Label>
              <Input
                id="python-ran-rrc-container"
                value={rrcContainer}
                onChange={(event) => setRrcContainer(event.target.value)}
              />
              <div className="text-muted-foreground">Control the RRC container content passed to the DU initial UL message.</div>
            </div>
          )}
          {selectedActionType === 'cu_create_rrc_setup' && (
            <div className="rounded border p-3 text-sm space-y-2">
              <Label htmlFor="python-ran-rrc-transaction-id">RRC transaction id</Label>
              <Input
                id="python-ran-rrc-transaction-id"
                type="number"
                min={1}
                value={rrcTransactionId}
                onChange={(event) => setRrcTransactionId(event.target.value)}
              />
              <Label htmlFor="python-ran-gnb-du-ue-id">gNB-DU UE F1AP id</Label>
              <Input
                id="python-ran-gnb-du-ue-id"
                type="number"
                min={1}
                value={gnbDuUeF1apId}
                onChange={(event) => setGnbDuUeF1apId(event.target.value)}
              />
              <div className="text-muted-foreground">Set both identifiers for the generated CU-side RRC setup message.</div>
            </div>
          )}
          {selectedActionType === 'du_process_prach' && (
            <div className="rounded border p-3 text-sm space-y-2">
              <Label htmlFor="python-ran-preamble-index">PRACH preamble index</Label>
              <Input
                id="python-ran-preamble-index"
                type="number"
                min={0}
                max={63}
                value={preambleIndex}
                onChange={(event) => setPreambleIndex(event.target.value)}
              />
              <div className="text-muted-foreground">Choose the PRACH preamble index for the DU PHY action.</div>
            </div>
          )}
          <div className="flex gap-2">
            <Button
              className="flex-1"
              disabled={!selectedActionType || submitting || !bridgeConnected}
              onClick={() => void onSubmit(selectedActionType, selectedParameters)}
            >
              <PlayCircle className="w-4 h-4 mr-2" />
              {submitting ? 'Submitting...' : 'Run Action'}
            </Button>
            <Button
              variant="outline"
              className="flex-1"
              disabled={!canApprove || approving || !latestAction?.action_id}
              onClick={() => latestAction?.action_id && void onApprove(latestAction.action_id)}
            >
              <ShieldCheck className="w-4 h-4 mr-2" />
              {approving ? 'Approving...' : 'Approve Latest'}
            </Button>
          </div>
        </div>

        <div className="rounded border p-3 space-y-3 text-sm">
          <div className="flex items-center justify-between gap-2">
            <div className="font-medium">Latest action</div>
            <div className="flex items-center gap-2">
              {latestStatusIcon}
              <Badge variant={latestStatusVariant}>{latestAction?.status ?? 'none'}</Badge>
              <Badge variant={latestVerificationVariant}>{latestEvidence?.verification_status ?? 'pending'}</Badge>
            </div>
          </div>
          {latestAction ? (
            <>
              <div>
                <div className="font-medium">{latestAction.summary ?? latestAction.action_type}</div>
                <div className="text-muted-foreground break-all">
                  {latestAction.action_id} • {latestAction.action_type}
                </div>
              </div>
              <div className="text-muted-foreground">
                Requested by {latestAction.requested_by ?? 'unknown'}
                {latestAction.approved_by ? ` • Approved by ${latestAction.approved_by}` : ''}
              </div>
              <div>{latestAction.result_summary ?? latestEvidence?.result_summary ?? 'No result summary yet'}</div>
              {!!latestAction.error_message && (
                <div className="rounded border border-red-200 bg-red-50 p-2 text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
                  {latestAction.error_message}
                </div>
              )}
              <div className="text-muted-foreground">
                Evidence refs: {latestEvidence?.evidence_refs?.length ?? latestAction.evidence_refs?.length ?? 0}
              </div>
            </>
          ) : (
            <div className="text-muted-foreground">No python RAN action has been submitted yet.</div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
