'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable'
import { DashboardHeader } from './DashboardHeader'
import { OcuduPanel } from './OcuduPanel'
import { PlaybookPanel } from './PlaybookPanel'
import { PythonRanPanel } from './PythonRanPanel'
import { SimulationControlPanel } from '@/components/controls/SimulationControlPanel'
import { NetworkTopologyView } from '@/components/network/NetworkTopologyView'
import { AnalyticsView } from '@/components/analytics/AnalyticsView'
import { OranView } from '@/components/oran/OranView'
import { Toaster } from '@/components/ui/sonner'
import {
  approveEiapAction,
  approvePythonRanAction,
  fetchFirewallStatus,
  fetchFactoryStatus,
  fetchLatestPlaybook,
  fetchLatestOcuduAction,
  fetchLatestOcuduEvidence,
  fetchLatestPythonRanAction,
  fetchLatestPythonRanEvidence,
  fetchLogs,
  fetchMetricsSummary,
  fetchNetworkStatus,
  fetchOcuduApps,
  fetchOcuduConfigs,
  fetchOcuduContext,
  fetchOcuduSupportedActions,
  fetchOcuduStatus,
  fetchPythonRanSupportedActions,
  generatePlaybook,
  submitOcuduAction,
  submitPythonRanAction,
  submitEiapAction,
  type FactoryPlaybook,
  type FactoryStatusResponse,
  type LogEntry,
  type MetricsPoint,
  type NetworkFunctionStatus,
  type OcuduAppsResponse,
  type OcuduActionRecord,
  type OcuduEvidenceRecord,
  type OcuduConfigsResponse,
  type OcuduContextResponse,
  type OcuduSupportedActionsResponse,
  type OcuduStatusResponse,
  type PythonRanActionRecord,
  type PythonRanEvidenceRecord,
  type PythonRanSupportedActionsResponse,
  type ThroughputPoint,
} from '@/lib/api'

export function MissionControlDashboard() {
  const [activeView, setActiveView] = useState<'dashboard' | 'analysis' | 'config' | 'oran'>('dashboard')
  const [selectedNF, setSelectedNF] = useState<string | null>(null)
  const [simulationStatus, setSimulationStatus] = useState<'stopped' | 'running' | 'paused'>('stopped')
  const [bridgeConnected, setBridgeConnected] = useState(false)
  const [networkFunctions, setNetworkFunctions] = useState<NetworkFunctionStatus[]>([])
  const [metricsData, setMetricsData] = useState<MetricsPoint[]>([])
  const [throughputData, setThroughputData] = useState<ThroughputPoint[]>([])
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [firewallLabel, setFirewallLabel] = useState('Bridge unavailable')
  const [refreshing, setRefreshing] = useState(false)
  const [latestPlaybook, setLatestPlaybook] = useState<FactoryPlaybook | null>(null)
  const [factoryStatus, setFactoryStatus] = useState<FactoryStatusResponse | null>(null)
  const [ocuduStatus, setOcuduStatus] = useState<OcuduStatusResponse | null>(null)
  const [ocuduApps, setOcuduApps] = useState<OcuduAppsResponse | null>(null)
  const [ocuduConfigs, setOcuduConfigs] = useState<OcuduConfigsResponse | null>(null)
  const [ocuduContext, setOcuduContext] = useState<OcuduContextResponse | null>(null)
  const [ocuduSupportedActions, setOcuduSupportedActions] = useState<OcuduSupportedActionsResponse | null>(null)
  const [latestOcuduAction, setLatestOcuduAction] = useState<OcuduActionRecord | null>(null)
  const [latestOcuduEvidence, setLatestOcuduEvidence] = useState<OcuduEvidenceRecord | null>(null)
  const [pythonRanSupportedActions, setPythonRanSupportedActions] = useState<PythonRanSupportedActionsResponse | null>(null)
  const [latestPythonRanAction, setLatestPythonRanAction] = useState<PythonRanActionRecord | null>(null)
  const [latestPythonRanEvidence, setLatestPythonRanEvidence] = useState<PythonRanEvidenceRecord | null>(null)
  const [generatingPlaybook, setGeneratingPlaybook] = useState(false)
  const [approvingPlaybook, setApprovingPlaybook] = useState(false)
  const [submittingPythonRanAction, setSubmittingPythonRanAction] = useState(false)
  const [approvingPythonRanAction, setApprovingPythonRanAction] = useState(false)
  const [submittingOcuduAction, setSubmittingOcuduAction] = useState(false)
  const [operatorBanner, setOperatorBanner] = useState('Ready')

  const refreshSnapshot = useCallback(async () => {
    setRefreshing(true)
    try {
      const [
        status,
        metrics,
        logPayload,
        firewall,
        latestPlaybookResponse,
        factoryStatusResponse,
        ocuduStatusResponse,
        ocuduAppsResponse,
        ocuduConfigsResponse,
        ocuduContextResponse,
        ocuduSupportedActionsResponse,
        latestOcuduActionResponse,
        latestOcuduEvidenceResponse,
        pythonRanSupportedActionsResponse,
        latestPythonRanActionResponse,
        latestPythonRanEvidenceResponse,
      ] = await Promise.all([
        fetchNetworkStatus(),
        fetchMetricsSummary(),
        fetchLogs(),
        fetchFirewallStatus(),
        fetchLatestPlaybook(),
        fetchFactoryStatus(),
        fetchOcuduStatus(),
        fetchOcuduApps(),
        fetchOcuduConfigs(),
        fetchOcuduContext(),
        fetchOcuduSupportedActions(),
        fetchLatestOcuduAction(),
        fetchLatestOcuduEvidence(),
        fetchPythonRanSupportedActions(),
        fetchLatestPythonRanAction(),
        fetchLatestPythonRanEvidence(),
      ])
      setNetworkFunctions(status.network_functions)
      setMetricsData(metrics.metrics)
      setThroughputData(metrics.throughput)
      setLogs(logPayload.logs)
      setFirewallLabel(`${firewall.status} • ${firewall.throughput ?? 'n/a'}`)
      setLatestPlaybook(latestPlaybookResponse.latest_playbook?.playbook ?? null)
      setFactoryStatus(factoryStatusResponse)
      setOcuduStatus(ocuduStatusResponse)
      setOcuduApps(ocuduAppsResponse)
      setOcuduConfigs(ocuduConfigsResponse)
      setOcuduContext(ocuduContextResponse)
      setOcuduSupportedActions(ocuduSupportedActionsResponse)
      setLatestOcuduAction(latestOcuduActionResponse.latest_action ?? factoryStatusResponse.latest_ocudu_action ?? null)
      setLatestOcuduEvidence(latestOcuduEvidenceResponse.latest_evidence ?? factoryStatusResponse.latest_ocudu_evidence ?? null)
      setPythonRanSupportedActions(pythonRanSupportedActionsResponse)
      setLatestPythonRanAction(latestPythonRanActionResponse.latest_action ?? factoryStatusResponse.latest_python_ran_action ?? null)
      setLatestPythonRanEvidence(latestPythonRanEvidenceResponse.latest_evidence ?? factoryStatusResponse.latest_python_ran_evidence ?? null)
      if (status.simulation_status) {
        setSimulationStatus(status.simulation_status)
      }
      setBridgeConnected(true)
    } catch {
      setBridgeConnected(false)
    } finally {
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void refreshSnapshot()
    const interval = setInterval(() => {
      void refreshSnapshot()
    }, 5000)
    return () => clearInterval(interval)
  }, [refreshSnapshot])

  const networkStats = useMemo(() => {
    const onlineNfs = networkFunctions.filter((nf) => nf.status === 'online').length || 8
    const activeSessions = networkFunctions.reduce((sum, nf) => sum + (nf.sessions ?? 0), 0) || 142
    const avgLatency = metricsData.length
      ? Math.round(metricsData.reduce((sum, point) => sum + (point.handoverDuration ?? 0), 0) / metricsData.length)
      : 23
    return { onlineNfs, activeSessions, avgLatency }
  }, [metricsData, networkFunctions])

  const handleGeneratePlaybook = useCallback(async () => {
    setGeneratingPlaybook(true)
    try {
      const incident = {
        incident_id: `INC-DEMO-${Date.now()}`,
        severity: 'high',
        domain: selectedNF ? `5G / ${selectedNF}` : 'OpenShift SNO / 5G edge site',
        site: 'metro-edge-dallas-07',
        affected_services: selectedNF ? [selectedNF] : ['distributed unit control-plane', 'edge API gateway'],
        symptoms: [
          selectedNF
            ? `${selectedNF} reported degraded behavior`
            : 'Multiple DU workloads restarted within 10 minutes',
          'Northbound API latency exceeded SLO',
        ],
        recent_changes: ['Prototype-generated demo playbook request'],
        telemetry_summary: {
          selected_nf: selectedNF ?? 'none',
          active_sessions: networkStats.activeSessions,
          avg_latency_ms: networkStats.avgLatency,
        },
      }
      const bundle = await generatePlaybook(incident)
      setLatestPlaybook(bundle.playbook)
      await submitEiapAction(bundle.action_proposal ?? { action_id: `playbook-${incident.incident_id}`, summary: bundle.playbook.title })
      setOperatorBanner(`Demo playbook generated for ${bundle.playbook.incident_id}`)
      await refreshSnapshot()
    } finally {
      setGeneratingPlaybook(false)
    }
  }, [networkStats.activeSessions, networkStats.avgLatency, refreshSnapshot, selectedNF])

  const handleApprovePlaybook = useCallback(async () => {
    if (!latestPlaybook) return
    setApprovingPlaybook(true)
    try {
      await approveEiapAction({
        action_id: `playbook-${latestPlaybook.incident_id}`,
        approved_by: 'dashboard-operator',
        decision: 'approved',
      })
      setOperatorBanner(`Approved ${latestPlaybook.incident_id}`)
      await refreshSnapshot()
    } finally {
      setApprovingPlaybook(false)
    }
  }, [latestPlaybook, refreshSnapshot])

  const handleSubmitPythonRanAction = useCallback(
    async (actionType: string, parameters?: Record<string, unknown>) => {
      setSubmittingPythonRanAction(true)
      try {
        const response = await submitPythonRanAction({
          action_type: actionType,
          summary: `Dashboard-triggered ${actionType}`,
          requested_by: 'dashboard-operator',
          parameters,
        })
        const action = response.action
        const status = action?.status ?? 'unknown'
        setOperatorBanner(`Python RAN action ${actionType} -> ${status}`)
        await refreshSnapshot()
      } finally {
        setSubmittingPythonRanAction(false)
      }
    },
    [refreshSnapshot]
  )

  const handleApprovePythonRanAction = useCallback(
    async (actionId: string) => {
      setApprovingPythonRanAction(true)
      try {
        const response = await approvePythonRanAction({
          action_id: actionId,
          approved_by: 'dashboard-operator',
        })
        setOperatorBanner(
          `Python RAN action ${response.action?.action_type ?? actionId} -> ${response.action?.status ?? 'unknown'}`
        )
        await refreshSnapshot()
      } finally {
        setApprovingPythonRanAction(false)
      }
    },
    [refreshSnapshot]
  )

  const handleSubmitOcuduAction = useCallback(
    async (actionType: string, parameters?: Record<string, unknown>) => {
      setSubmittingOcuduAction(true)
      try {
        const response = await submitOcuduAction({
          action_type: actionType,
          summary: `Dashboard-triggered ${actionType}`,
          requested_by: 'dashboard-operator',
          parameters,
        })
        setOperatorBanner(`OCUDU action ${response.action?.action_type ?? actionType} -> ${response.action?.status ?? 'unknown'}`)
        await refreshSnapshot()
      } finally {
        setSubmittingOcuduAction(false)
      }
    },
    [refreshSnapshot]
  )

  const handleStartDemo = useCallback(() => {
    setSimulationStatus('running')
    setActiveView('analysis')
    setSelectedNF((current) => current ?? 'AMF')
    setOperatorBanner('Start pressed: switched to Procedure Analysis and running demo flow')
    if (!latestPlaybook && !generatingPlaybook) {
      void handleGeneratePlaybook()
    } else {
      void refreshSnapshot()
    }
  }, [generatingPlaybook, handleGeneratePlaybook, latestPlaybook, refreshSnapshot])

  const fallbackMetricsData = useMemo<MetricsPoint[]>(
    () => [
      { time: '14:30', handoverDuration: 85, registrations: 12, sessions: 23 },
      { time: '14:31', handoverDuration: 92, registrations: 8, sessions: 25 },
      { time: '14:32', handoverDuration: 78, registrations: 15, sessions: 28 },
      { time: '14:33', handoverDuration: 88, registrations: 11, sessions: 26 },
      { time: '14:34', handoverDuration: 95, registrations: 9, sessions: 30 },
      { time: '14:35', handoverDuration: 82, registrations: 13, sessions: 32 },
    ],
    []
  )

  const fallbackThroughputData = useMemo<ThroughputPoint[]>(
    () => [
      { time: '14:30', upf: 120, firewall: 118, dropped: 2 },
      { time: '14:31', upf: 145, firewall: 142, dropped: 3 },
      { time: '14:32', upf: 163, firewall: 160, dropped: 3 },
      { time: '14:33', upf: 178, firewall: 175, dropped: 3 },
      { time: '14:34', upf: 156, firewall: 152, dropped: 4 },
      { time: '14:35', upf: 171, firewall: 168, dropped: 3 },
    ],
    []
  )

  const fallbackLogs = useMemo<LogEntry[]>(
    () => [
      { id: 1, timestamp: '2024-08-14 14:35:23', nf: 'AMF', level: 'INFO', message: 'UE ue001 successfully registered with gNB gnb001' },
      { id: 2, timestamp: '2024-08-14 14:35:22', nf: 'SMF', level: 'INFO', message: 'PDU session established for UE ue001' },
      { id: 3, timestamp: '2024-08-14 14:35:21', nf: 'UPF', level: 'WARN', message: 'High packet rate detected from UE ue002' },
      { id: 4, timestamp: '2024-08-14 14:35:20', nf: 'BF3-FW', level: 'INFO', message: 'Blocked 127 packets on port 8001 (firewall rule match)' },
      { id: 5, timestamp: '2024-08-14 14:35:19', nf: 'gNB-CU', level: 'ERROR', message: 'Failed to establish connection with UE ue003' },
    ],
    []
  )

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Header */}
      <DashboardHeader 
        simulationStatus={simulationStatus}
        onSimulationToggle={(status) => setSimulationStatus(status)}
        onStartDemo={handleStartDemo}
        activeView={activeView}
        onViewChange={setActiveView}
        networkStats={networkStats}
      />
      
      {/* Main Dashboard Layout */}
      <div className="flex-1 p-4">
        <ResizablePanelGroup direction="horizontal" className="h-full rounded-lg border">
          
          {/* Left Panel: Simulation Control */}
          <ResizablePanel defaultSize={25} minSize={20} maxSize={35}>
            <div className="p-4 h-full">
              <SimulationControlPanel 
                onSimulationToggle={setSimulationStatus}
                selectedNF={selectedNF}
                onNFSelect={setSelectedNF}
                onOpenConfig={() => setActiveView('config')}
                networkFunctions={networkFunctions}
                factoryStatus={factoryStatus}
              />
              <PlaybookPanel
                playbook={latestPlaybook}
                factoryStatus={factoryStatus}
                generating={generatingPlaybook}
                approving={approvingPlaybook}
                bridgeConnected={bridgeConnected}
                onGenerate={handleGeneratePlaybook}
                onApprove={handleApprovePlaybook}
              />
              <OcuduPanel
                status={ocuduStatus}
                apps={ocuduApps}
                configs={ocuduConfigs}
                context={ocuduContext}
                supportedActions={ocuduSupportedActions}
                latestAction={latestOcuduAction}
                latestEvidence={latestOcuduEvidence}
                submitting={submittingOcuduAction}
                onSubmit={handleSubmitOcuduAction}
                bridgeConnected={bridgeConnected}
              />
              <PythonRanPanel
                supportedActions={pythonRanSupportedActions}
                latestAction={latestPythonRanAction}
                latestEvidence={latestPythonRanEvidence}
                bridgeConnected={bridgeConnected}
                submitting={submittingPythonRanAction}
                approving={approvingPythonRanAction}
                onSubmit={handleSubmitPythonRanAction}
                onApprove={handleApprovePythonRanAction}
              />
            </div>
          </ResizablePanel>
          
          <ResizableHandle withHandle />
          
          {/* Center Panel: Network Topology */}
          <ResizablePanel defaultSize={50} minSize={30}>
            <ResizablePanelGroup direction="vertical">
              
              {/* Main Network View */}
              <ResizablePanel defaultSize={70} minSize={40}>
                <div className="p-4 h-full">
                  {activeView === 'oran' ? (
                    <OranView />
                  ) : activeView === 'config' ? (
                    <div className="h-full rounded-lg border bg-muted/20 p-6 text-sm text-muted-foreground">
                      <div className="space-y-3">
                        <div className="text-lg font-semibold text-foreground">Configuration Mode</div>
                        <div className="rounded border bg-background p-3 text-foreground">{operatorBanner}</div>
                        <div>This mode was activated by the header or firewall controls.</div>
                        <div>
                          Current focus: <span className="font-medium text-foreground">{selectedNF ?? 'none selected'}</span>
                        </div>
                        <div>Use the left-side controls and AI Factory Playbook panel to work with the prototype.</div>
                      </div>
                    </div>
                  ) : activeView === 'analysis' ? (
                    <div className="h-full rounded-lg border bg-muted/20 p-6 text-sm text-muted-foreground">
                      <div className="space-y-3">
                        <div className="text-lg font-semibold text-foreground">Procedure Analysis Mode</div>
                        <div className="rounded border bg-background p-3 text-foreground">{operatorBanner}</div>
                        <div>This mode was activated by the header view switch.</div>
                        <div>
                          Selected context: <span className="font-medium text-foreground">{selectedNF ?? 'all network functions'}</span>
                        </div>
                        <div>
                          Latest playbook: <span className="font-medium text-foreground">{latestPlaybook?.title ?? 'none yet'}</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <NetworkTopologyView 
                      selectedNF={selectedNF}
                      onNFSelect={setSelectedNF}
                      simulationStatus={simulationStatus}
                      networkFunctions={networkFunctions}
                      bridgeConnected={bridgeConnected}
                    />
                  )}
                </div>
              </ResizablePanel>
              
              <ResizableHandle withHandle />
              
              {/* Bottom Panel: Analytics */}
              <ResizablePanel defaultSize={30} minSize={20}>
                <div className="p-4 h-full">
                  <AnalyticsView 
                    selectedNF={selectedNF}
                    simulationStatus={activeView === 'analysis' ? 'running' : simulationStatus}
                    metricsData={metricsData.length ? metricsData : fallbackMetricsData}
                    throughputData={throughputData.length ? throughputData : fallbackThroughputData}
                    logs={logs.length ? logs : fallbackLogs}
                    bridgeConnected={bridgeConnected}
                    firewallLabel={firewallLabel}
                    refreshing={refreshing}
                    onRefresh={refreshSnapshot}
                  />
                </div>
              </ResizablePanel>
              
            </ResizablePanelGroup>
          </ResizablePanel>
          
        </ResizablePanelGroup>
      </div>
      
      {/* Toast Notifications */}
      <Toaster />
    </div>
  )
}
