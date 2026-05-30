'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { 
  Play, 
  ChevronDown,
  ChevronRight,
  Smartphone,
  AlertTriangle,
  Zap,
  Shield,
  Settings
} from 'lucide-react'
import { toast } from 'sonner'
import {
  type FactoryStatusResponse,
  triggerSimulationAnomaly,
  triggerSimulationProcedure,
  type NetworkFunctionStatus,
  type SimulationActionResponse,
} from '@/lib/api'

interface SimulationControlPanelProps {
  onSimulationToggle: (status: 'stopped' | 'running' | 'paused') => void
  selectedNF: string | null
  onNFSelect: (nf: string | null) => void
  onOpenConfig: () => void
  networkFunctions?: NetworkFunctionStatus[]
  factoryStatus?: FactoryStatusResponse | null
}

export function SimulationControlPanel({ 
  onSimulationToggle, 
  selectedNF,
  onNFSelect,
  onOpenConfig,
  networkFunctions = [],
  factoryStatus = null,
}: SimulationControlPanelProps) {
  const [selectedProcedure, setSelectedProcedure] = useState('')
  const [ueId, setUeId] = useState('')
  const [anomalyType, setAnomalyType] = useState('')
  const [anomalyIntensity, setAnomalyIntensity] = useState([50])
  const [sidebarExpanded, setSidebarExpanded] = useState({
    coreNFs: true,
    ranNFs: true,
    activeUEs: false
  })

  // Mock data for UEs
  const mockUEs = [
    { id: 'ue001', status: 'Registered', gnb: 'gnb001', sessions: 2 },
    { id: 'ue002', status: 'Connected', gnb: 'gnb001', sessions: 1 },
    { id: 'ue003', status: 'Idle', gnb: 'gnb002', sessions: 0 },
  ]
  const [ues, setUes] = useState(mockUEs)

  const normalizedNfs = networkFunctions.map((nf) => ({
    name: nf.label,
    status: nf.status,
    load: nf.load,
    id: nf.id,
  }))

  const pythonRanComponents = (factoryStatus?.python_ran as { components?: Record<string, unknown> } | undefined)?.components ?? {}
  const pythonRanRans = Object.entries(pythonRanComponents).map(([key, value]) => {
    const component = (value as Record<string, unknown>) ?? {}
    const status = String(component.status ?? 'unknown')
    return {
      id: `python-ran-${key}`,
      name:
        key === 'gnb'
          ? 'gNB'
          : key.toUpperCase(),
      status,
      load: component.live ? 55 : 10,
    }
  })

  const coreNFs = normalizedNfs.filter((nf) => !nf.name.toLowerCase().includes('gnb'))
  const ranNFs = normalizedNfs.filter((nf) => nf.name.toLowerCase().includes('gnb'))
  const effectiveRanNfs = ranNFs.length ? ranNFs : pythonRanRans

  const procedures = [
    'UE Initial Registration',
    'PDU Session Establishment',
    'Xn Handover',
    'N2 Handover',
    'Service Request',
    'UE Context Release'
  ]

  const anomalies = [
    'AMF Latency Spike',
    'UPF Packet Drop',
    'gNB Connection Loss',
    'Database Timeout',
    'Network Congestion'
  ]

  const describeResponse = (response: SimulationActionResponse) => {
    if (response.mode === 'live-http') {
      return `Live adapter hit ${response.adapter_target ?? 'bridge target'}`
    }
    if (response.mode === 'fallback-plan') {
      return response.next_step ?? 'Bridge accepted the request in fallback mode'
    }
    if (response.mode === 'unsupported-procedure') {
      return response.next_step ?? 'Procedure is not yet mapped'
    }
    return response.next_step ?? response.mode
  }

  const handleProcedureTrigger = async () => {
    if (!selectedProcedure || !ueId) {
      toast.error('Please select a procedure and enter UE ID')
      return
    }
    try {
      const response = await triggerSimulationProcedure({
        procedure: selectedProcedure,
        ueId,
        selectedNF,
      })
      if (response.mode === 'live-http') {
        toast.success(`Triggered ${selectedProcedure} for UE ${ueId}`, {
          description: describeResponse(response),
        })
        onSimulationToggle('running')
      } else if (response.mode === 'unsupported-procedure') {
        toast.warning(`${selectedProcedure} is not fully wired yet`, {
          description: describeResponse(response),
        })
      } else {
        toast.message(`Queued ${selectedProcedure} for UE ${ueId}`, {
          description: describeResponse(response),
        })
      }
    } catch (error) {
      toast.error(`Failed to trigger ${selectedProcedure}`, {
        description: error instanceof Error ? error.message : 'Unknown bridge error',
      })
    }
  }

  const handleAnomalyInject = async () => {
    if (!anomalyType) {
      toast.error('Please select an anomaly type')
      return
    }
    try {
      const response = await triggerSimulationAnomaly({
        anomalyType,
        intensity: anomalyIntensity[0],
        selectedNF,
      })
      if (response.mode === 'live-http') {
        toast.warning(`Injected ${anomalyType} with ${anomalyIntensity[0]}% intensity`, {
          description: describeResponse(response),
        })
      } else {
        toast.message(`Prepared ${anomalyType} at ${anomalyIntensity[0]}% intensity`, {
          description: describeResponse(response),
        })
      }
    } catch (error) {
      toast.error(`Failed to inject ${anomalyType}`, {
        description: error instanceof Error ? error.message : 'Unknown bridge error',
      })
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online': return 'bg-green-500'
      case 'degraded': return 'bg-yellow-500'
      case 'offline': return 'bg-red-500'
      default: return 'bg-gray-500'
    }
  }

  return (
    <div className="space-y-4 h-full overflow-y-auto">
      
      {/* Context Sidebar */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center">
            <Settings className="w-5 h-5 mr-2" />
            Network Context
          </CardTitle>
          <CardDescription>Filter dashboard by network component</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          
          {/* Core Network Functions */}
          <Collapsible 
            open={sidebarExpanded.coreNFs} 
            onOpenChange={(open) => setSidebarExpanded(prev => ({ ...prev, coreNFs: open }))}
          >
            <CollapsibleTrigger className="flex items-center space-x-2 w-full text-left">
              {sidebarExpanded.coreNFs ? 
                <ChevronDown className="w-4 h-4" /> : 
                <ChevronRight className="w-4 h-4" />
              }
              <span className="font-medium">Core Network</span>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-2 mt-2 ml-6">
              {coreNFs.length ? coreNFs.map((nf) => (
                <div 
                  key={nf.id}
                  className={`flex items-center justify-between p-2 rounded cursor-pointer hover:bg-muted ${
                    selectedNF === nf.name ? 'bg-muted' : ''
                  }`}
                  onClick={() => onNFSelect(selectedNF === nf.name ? null : nf.name)}
                >
                  <div className="flex items-center space-x-2">
                    <div className={`w-2 h-2 rounded-full ${getStatusColor(nf.status)}`} />
                    <span className="text-sm font-medium">{nf.name}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Progress value={nf.load} className="w-12 h-2" />
                    <span className="text-xs text-muted-foreground">{nf.load}%</span>
                  </div>
                </div>
              )) : (
                <div className="text-sm text-muted-foreground">No live core network data</div>
              )}
            </CollapsibleContent>
          </Collapsible>

          {/* RAN Network Functions */}
          <Collapsible 
            open={sidebarExpanded.ranNFs} 
            onOpenChange={(open) => setSidebarExpanded(prev => ({ ...prev, ranNFs: open }))}
          >
            <CollapsibleTrigger className="flex items-center space-x-2 w-full text-left">
              {sidebarExpanded.ranNFs ? 
                <ChevronDown className="w-4 h-4" /> : 
                <ChevronRight className="w-4 h-4" />
              }
              <span className="font-medium">RAN Components</span>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-2 mt-2 ml-6">
              {effectiveRanNfs.length ? effectiveRanNfs.map((nf) => (
                <div 
                  key={nf.id}
                  className={`flex items-center justify-between p-2 rounded cursor-pointer hover:bg-muted ${
                    selectedNF === nf.name ? 'bg-muted' : ''
                  }`}
                  onClick={() => onNFSelect(selectedNF === nf.name ? null : nf.name)}
                >
                  <div className="flex items-center space-x-2">
                    <div className={`w-2 h-2 rounded-full ${getStatusColor(nf.status)}`} />
                    <span className="text-sm font-medium">{nf.name}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Progress value={nf.load} className="w-12 h-2" />
                    <span className="text-xs text-muted-foreground">{nf.load}%</span>
                  </div>
                </div>
              )) : (
                <div className="text-sm text-muted-foreground">No live RAN component data</div>
              )}
            </CollapsibleContent>
          </Collapsible>

        </CardContent>
      </Card>

      {/* Simulation Controls */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center">
            <Play className="w-5 h-5 mr-2" />
            Simulation Control
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Accordion type="single" collapsible className="w-full">
            
            {/* Trigger Procedure */}
            <AccordionItem value="procedures">
              <AccordionTrigger className="text-base">
                <div className="flex items-center">
                  <Zap className="w-4 h-4 mr-2" />
                  Trigger Procedure
                </div>
              </AccordionTrigger>
              <AccordionContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="procedure">5G Procedure</Label>
                  <Select value={selectedProcedure} onValueChange={setSelectedProcedure}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a 5G procedure..." />
                    </SelectTrigger>
                    <SelectContent>
                      {procedures.map((procedure) => (
                        <SelectItem key={procedure} value={procedure}>
                          {procedure}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ue-id">UE ID</Label>
                  <Input
                    id="ue-id"
                    placeholder="e.g., ue001"
                    value={ueId}
                    onChange={(e) => setUeId(e.target.value)}
                  />
                </div>
                <Button onClick={handleProcedureTrigger} className="w-full">
                  <Play className="w-4 h-4 mr-2" />
                  Execute Procedure
                </Button>
              </AccordionContent>
            </AccordionItem>

            {/* Inject Anomaly */}
            <AccordionItem value="anomalies">
              <AccordionTrigger className="text-base">
                <div className="flex items-center">
                  <AlertTriangle className="w-4 h-4 mr-2" />
                  Inject Anomaly
                </div>
              </AccordionTrigger>
              <AccordionContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="anomaly">Anomaly Type</Label>
                  <Select value={anomalyType} onValueChange={setAnomalyType}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select anomaly..." />
                    </SelectTrigger>
                    <SelectContent>
                      {anomalies.map((anomaly) => (
                        <SelectItem key={anomaly} value={anomaly}>
                          {anomaly}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Intensity: {anomalyIntensity[0]}%</Label>
                  <Slider
                    value={anomalyIntensity}
                    onValueChange={setAnomalyIntensity}
                    max={100}
                    step={1}
                    className="w-full"
                  />
                </div>
                <Button onClick={handleAnomalyInject} variant="destructive" className="w-full">
                  <AlertTriangle className="w-4 h-4 mr-2" />
                  Inject Anomaly
                </Button>
              </AccordionContent>
            </AccordionItem>

            {/* Manage UEs */}
            <AccordionItem value="ues">
              <AccordionTrigger className="text-base">
                <div className="flex items-center">
                  <Smartphone className="w-4 h-4 mr-2" />
                  Manage UEs ({mockUEs.length})
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-3">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>UE ID</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Sessions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {ues.map((ue) => (
                        <TableRow key={ue.id}>
                          <TableCell className="font-medium">{ue.id}</TableCell>
                          <TableCell>
                            <Badge
                              variant={
                                ue.status.toLowerCase() === 'registered' || ue.status.toLowerCase() === 'connected'
                                  ? 'default'
                                  : ue.status.toLowerCase() === 'idle'
                                    ? 'secondary'
                                    : ue.status.toLowerCase() === 'offline'
                                      ? 'destructive'
                                      : 'outline'
                              }
                            >
                              {ue.status}
                            </Badge>
                          </TableCell>
                          <TableCell>{ue.sessions}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  <Button
                    size="sm"
                    className="w-full"
                    onClick={() => {
                      const nextId = `ue${String(ues.length + 1).padStart(3, '0')}`
                      setUes((prev) => [...prev, { id: nextId, status: 'Idle', gnb: 'gnb002', sessions: 0 }])
                      toast.success(`Added demo UE ${nextId}`)
                    }}
                  >
                    <Smartphone className="w-4 h-4 mr-2" />
                    Add New UE
                  </Button>
                </div>
              </AccordionContent>
            </AccordionItem>

          </Accordion>
        </CardContent>
      </Card>

      {/* N6 Interface Firewall Controls */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center">
            <Shield className="w-5 h-5 mr-2" />
            N6 Firewall
          </CardTitle>
          <CardDescription>BlueField-3 DPU Controls</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Hardware Acceleration</span>
            <Badge variant="default">DOCA Active</Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Throughput</span>
            <span className="text-sm text-muted-foreground">156 Gbps</span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Packets Processed</span>
              <span>1.2M</span>
            </div>
            <Progress value={65} className="w-full" />
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Packets Dropped</span>
              <span>48K</span>
            </div>
            <Progress value={25} className="w-full" />
          </div>
          <Button
            size="sm"
            className="w-full"
            variant="outline"
            onClick={() => {
              onNFSelect('BF3-FW')
              onOpenConfig()
              toast.message('Opened Configuration mode for BF3 firewall', {
                description: 'Use the center panel as the configuration workspace in this prototype.',
              })
            }}
          >
            <Settings className="w-4 h-4 mr-2" />
            Configure Rules
          </Button>
        </CardContent>
      </Card>

    </div>
  )
}
